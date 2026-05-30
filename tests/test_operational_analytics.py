"""Tests for the Operational Analytics Layer (V3-P5).

Covers the analytics registry, the six engines (metrics, health, performance,
quality, trend, risk), analytics lineage, validation, determinism, and the
governance gate — over analytics derived from real events/workflows/graph/temporal.
"""

from __future__ import annotations

import pytest

from backend.operational_analytics import (
    AnalyticsCategory, AnalyticsGovernanceGate, AnalyticsRegistry,
    AnalyticsRecord, AnalyticsMetric, AnalyticsSourceRef,
)

from _v3c_helpers import build_v3c


@pytest.fixture(scope="module")
def fx():
    return build_v3c(2)


# --- registry -----------------------------------------------------------------
def test_no_analytics_outside_registry(fx):
    for category, rec in fx.analytics_records.items():
        assert fx.analytics.registry.exists(rec.analytics_id)
        assert fx.analytics.registry.get(rec.analytics_id).version == rec.version


def test_registry_rejects_silent_overwrite():
    from backend.operational_analytics.models import AnalyticsRegistryRecord
    reg = AnalyticsRegistry()
    rec = AnalyticsRegistryRecord(analytics_id="analytics+" + "a" * 16, category="metrics",
                                  scope="metrics:operational:all", subject_id="all", version="v1",
                                  lineage_id="lineage+" + "b" * 16, audit_state="h",
                                  content_signature_value="sig-1")
    reg.register(rec)
    bad = AnalyticsRegistryRecord(analytics_id="analytics+" + "a" * 16, category="metrics",
                                  scope="metrics:operational:all", subject_id="all", version="v1",
                                  lineage_id="lineage+" + "b" * 16, audit_state="h",
                                  content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


def test_all_categories_present(fx):
    assert set(fx.analytics_records) == {
        AnalyticsCategory.METRICS, AnalyticsCategory.HEALTH, AnalyticsCategory.PERFORMANCE,
        AnalyticsCategory.QUALITY, AnalyticsCategory.TREND, AnalyticsCategory.RISK,
        AnalyticsCategory.OPERATIONAL}


# --- metrics engine -----------------------------------------------------------
def test_metrics_engine(fx):
    rec = fx.analytics_records[AnalyticsCategory.METRICS]
    assert rec.metric("event_total").value > 0
    assert rec.metric("workflow_total").value > 0
    assert rec.metric("graph_node_count").value > 0
    # every metric is explainable
    assert all(m.explanation for m in rec.metrics)


# --- health engine ------------------------------------------------------------
def test_health_engine_scores_bounded_and_explainable(fx):
    rec = fx.analytics_records[AnalyticsCategory.HEALTH]
    names = {m.name for m in rec.metrics}
    assert {"operational_health", "system_health_score", "case_health", "graph_health"} <= names
    for m in rec.metrics:
        assert 0.0 <= m.value <= 1.0
        assert m.explanation


# --- performance engine -------------------------------------------------------
def test_performance_engine(fx):
    rec = fx.analytics_records[AnalyticsCategory.PERFORMANCE]
    names = {m.name for m in rec.metrics}
    assert {"completion_performance", "operational_efficiency", "velocity"} <= names
    # case workflows completed -> completion performance == 1.0
    assert rec.metric("completion_performance").value == 1.0


# --- quality engine -----------------------------------------------------------
def test_quality_engine(fx):
    rec = fx.analytics_records[AnalyticsCategory.QUALITY]
    names = {m.name for m in rec.metrics}
    assert {"workflow_quality", "graph_integrity", "analytics_integrity"} <= names
    # graph integrity: all edges reference registered endpoints
    assert rec.metric("graph_integrity").value == 1.0


# --- trend engine -------------------------------------------------------------
def test_trend_engine_indices_in_range(fx):
    rec = fx.analytics_records[AnalyticsCategory.TREND]
    names = {m.name for m in rec.metrics}
    assert {"operational_trend", "temporal_volume_trend", "review_trend"} <= names
    for m in rec.metrics:
        assert -1.0 <= m.value <= 1.0


# --- risk engine --------------------------------------------------------------
def test_risk_engine_scores_bounded(fx):
    rec = fx.analytics_records[AnalyticsCategory.RISK]
    names = {m.name for m in rec.metrics}
    assert {"operational_risk", "workflow_risk", "bottleneck_risk", "dependency_risk",
            "quality_risk", "knowledge_risk"} <= names
    for m in rec.metrics:
        assert 0.0 <= m.value <= 1.0


def test_risk_engine_emits_no_recommendations(fx):
    """The risk engine produces risks only — never guidance/recommendation text."""
    rec = fx.analytics_records[AnalyticsCategory.RISK]
    assert all(m.dimension == "risk" and m.unit == "score" for m in rec.metrics)


# --- lineage / validation / determinism ---------------------------------------
def test_analytics_lineage_traces_to_patient(fx):
    tracker = fx.base.base.cs.lineage
    for rec in fx.analytics_records.values():
        kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
        assert {"analytics", "workflow", "event", "case", "patient"} <= kinds
        assert tracker.verify_chain(rec.lineage_id)


def test_full_analytics_validation_passes(fx):
    for rec in fx.analytics_records.values():
        rep = fx.analytics.validate(rec).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"metric_integrity", "health_integrity", "trend_integrity", "risk_integrity",
                "registry_integrity", "audit_integrity", "lineage_integrity",
                "version_integrity"} <= names
        assert rep["ok"], rep


def test_governance_gate_rejects_underived_analytics():
    """An analytics record with no upstream sources is not derived -> rejected."""
    rec = AnalyticsRecord(analytics_id="analytics+" + "0" * 16, category="metrics",
                          scope="metrics:operational:all", subject_kind="operational",
                          subject_id="all",
                          metrics=(AnalyticsMetric("x", 0.5, "ratio", True, "metrics", "explained"),),
                          sources=())
    gate = AnalyticsGovernanceGate()
    report = gate.evaluate(record=rec, parents=(), requires_lineage=False)
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}


def test_governance_gate_accepts_derived_analytics():
    src = AnalyticsSourceRef("workflow+" + "a" * 16, "workflow", "lineage+" + "b" * 16)
    rec = AnalyticsRecord(analytics_id="analytics+" + "0" * 16, category="health",
                          scope="health:operational:all", subject_kind="operational",
                          subject_id="all",
                          metrics=(AnalyticsMetric("h", 0.8, "score", True, "health", "explained"),),
                          sources=(src,))
    gate = AnalyticsGovernanceGate()
    report = gate.evaluate(record=rec, parents=("lineage+" + "b" * 16,), requires_lineage=True)
    assert report.ok, report.to_dict()


def test_analytics_audit_verifies(fx):
    assert fx.analytics.audit.verify()
    assert len(fx.analytics.audit) > 0


def test_analytics_is_reproducible():
    a = build_v3c(2)
    b = build_v3c(2)
    a_sigs = sorted(r.state_signature() for r in a.analytics_records.values())
    b_sigs = sorted(r.state_signature() for r in b.analytics_records.values())
    assert a_sigs == b_sigs


def test_analytics_does_not_mutate_sources(fx):
    """Analytics is derived intelligence; building it must not change source truth."""
    case_id = next(iter(fx.base.base.cases))
    before = fx.base.base.cs.registry.get(case_id).content_signature()
    fx.analytics.build_operational()
    after = fx.base.base.cs.registry.get(case_id).content_signature()
    assert before == after


def test_reports_are_versioned(fx):
    reports = fx.analytics.reports(list(fx.analytics_records.values()))
    assert reports["health_report"]["analytics_report_version"]
    assert reports["risk_report"]["report_type"] == "analytics_risk"
    assert reports["audit_report"]["verified"]
