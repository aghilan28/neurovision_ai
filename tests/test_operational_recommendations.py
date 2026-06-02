"""Tests for the Operational Recommendation Layer (V3-P6).

Covers the recommendation registry, the engines (context, guidance, prioritization,
optimization, escalation), recommendation lineage, validation, determinism, and the
governance gate — over recommendations derived from real analytics/workflows/graph.
"""

from __future__ import annotations

import pytest

from backend.operational_recommendations import (
    RecommendationKind, PriorityLevel, RecommendationGovernanceGate, RecommendationRegistry,
    RecommendationRecord, RecommendationPriority, RecommendationEvidence, level_for_score,
)

from _v3c_helpers import build_v3c, all_recommendations


@pytest.fixture(scope="module")
def fx():
    return build_v3c(2)


def _make_priority(level=PriorityLevel.MEDIUM, score=0.3):
    return RecommendationPriority(level=level, score=score, reason="test")


# --- registry -----------------------------------------------------------------
def test_no_recommendation_outside_registry(fx):
    for rec in all_recommendations(fx):
        assert fx.recommendations.registry.exists(rec.recommendation_id)
        assert fx.recommendations.registry.get(rec.recommendation_id).version == rec.version


def test_registry_rejects_silent_overwrite():
    from backend.operational_recommendations.models import RecommendationRegistryRecord
    reg = RecommendationRegistry()
    rec = RecommendationRegistryRecord(recommendation_id="recommendation+" + "a" * 16,
                                       kind="guidance", scope="guidance:workflow:all",
                                       subject_id="all", priority_level="medium", version="v1",
                                       lineage_id="lineage+" + "b" * 16, audit_state="h",
                                       content_signature_value="sig-1")
    reg.register(rec)
    bad = RecommendationRegistryRecord(recommendation_id="recommendation+" + "a" * 16,
                                       kind="guidance", scope="guidance:workflow:all",
                                       subject_id="all", priority_level="medium", version="v1",
                                       lineage_id="lineage+" + "b" * 16, audit_state="h",
                                       content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


def test_kinds_present(fx):
    kinds = {r.kind for r in all_recommendations(fx)}
    assert RecommendationKind.GUIDANCE in kinds
    assert RecommendationKind.OPTIMIZATION in kinds
    assert RecommendationKind.ESCALATION in kinds


# --- context engine -----------------------------------------------------------
def test_context_engine_aggregates_all_dimensions(fx):
    cid = fx.recommendation_records["guidance"][0].context_id
    ctx = fx.recommendations.registry.context(cid)
    assert ctx.analytics_context and ctx.workflow_context and ctx.graph_context
    assert ctx.risk_context and ctx.health_context
    # context is registered and traceable to a context id
    assert fx.recommendations.registry.has_context(cid)


# --- guidance engine ----------------------------------------------------------
def test_guidance_engine_items_cite_evidence(fx):
    guidance = fx.recommendation_records["guidance"]
    assert len(guidance) >= 1
    for rec in guidance:
        assert rec.n_evidence > 0
        assert any(e.source_kind == "analytics" for e in rec.evidence)
        assert rec.statement and rec.rationale


# --- prioritization engine ----------------------------------------------------
def test_prioritization_banding():
    assert level_for_score(0.9) == PriorityLevel.CRITICAL
    assert level_for_score(0.6) == PriorityLevel.HIGH
    assert level_for_score(0.3) == PriorityLevel.MEDIUM
    assert level_for_score(0.1) == PriorityLevel.LOW


def test_prioritization_is_explainable(fx):
    for rec in all_recommendations(fx):
        p = rec.priority
        assert p.reason
        assert level_for_score(p.score) == p.level
        # at least one supporting signal is recorded
        assert (p.supporting_metrics or p.supporting_risks or p.supporting_trends
                or p.supporting_workflow)


# --- optimization engine ------------------------------------------------------
def test_optimization_suggestions_only(fx):
    opt = fx.recommendation_records["optimization"]
    assert len(opt) >= 1
    for rec in opt:
        assert rec.kind == RecommendationKind.OPTIMIZATION
        # a suggestion is described, never executed
        assert "Suggestion" in rec.statement
        assert rec.n_evidence > 0


# --- escalation framework -----------------------------------------------------
def test_escalation_candidates_have_risk_context(fx):
    esc = fx.recommendation_records["escalation"]
    # the synthetic fixture has elevated knowledge risk -> at least one candidate
    assert len(esc) >= 1
    for rec in esc:
        assert rec.kind == RecommendationKind.ESCALATION
        assert "no automatic escalation" in rec.statement.lower()
        # risk-context evidence is attached
        assert any(e.metric_name == "risk_context" for e in rec.evidence)
        assert rec.priority.supporting_risks


# --- lineage / validation / determinism ---------------------------------------
def test_recommendation_lineage_traces_to_patient(fx):
    tracker = fx.base.base.cs.lineage
    for rec in all_recommendations(fx):
        kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
        assert {"recommendation", "analytics", "workflow", "event", "case", "patient"} <= kinds
        assert tracker.verify_chain(rec.lineage_id)


def test_full_recommendation_validation_passes(fx):
    for rec in all_recommendations(fx):
        rep = fx.recommendations.validate(rec).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"context_integrity", "evidence_integrity", "priority_integrity",
                "guidance_integrity", "registry_integrity", "audit_integrity",
                "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_gate_rejects_black_box_recommendation():
    """A recommendation with no evidence/analytics link is a black box -> rejected."""
    rec = RecommendationRecord(
        recommendation_id="recommendation+" + "0" * 16, kind="guidance",
        scope="guidance:workflow:all", subject_kind="workflow", subject_id="all",
        statement="do something", priority=_make_priority(), evidence=(), analytics_ids=(),
        rationale="because")
    gate = RecommendationGovernanceGate()
    report = gate.evaluate(record=rec, parents=(), requires_lineage=False)
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}


def test_gate_accepts_evidence_and_analytics_linked():
    ev = RecommendationEvidence(evidence_id="evidence+" + "a" * 16, source_kind="analytics",
                                source_id="analytics+" + "c" * 16, metric_name="operational_risk",
                                value=0.6, lineage_id="lineage+" + "b" * 16)
    rec = RecommendationRecord(
        recommendation_id="recommendation+" + "0" * 16, kind="escalation",
        scope="escalation:operational:all", subject_kind="operational", subject_id="all",
        statement="escalation candidate; no automatic escalation taken",
        priority=_make_priority(PriorityLevel.HIGH, 0.6), evidence=(ev,),
        analytics_ids=("analytics+" + "c" * 16,), rationale="derived from operational_risk")
    gate = RecommendationGovernanceGate()
    report = gate.evaluate(record=rec, parents=("lineage+" + "b" * 16,), requires_lineage=True)
    assert report.ok, report.to_dict()


def test_recommendation_audit_verifies(fx):
    assert fx.recommendations.audit.verify()
    assert len(fx.recommendations.audit) > 0


def test_recommendation_is_reproducible():
    a = build_v3c(2)
    b = build_v3c(2)
    a_sigs = sorted(r.state_signature() for r in all_recommendations(a))
    b_sigs = sorted(r.state_signature() for r in all_recommendations(b))
    assert a_sigs == b_sigs


def test_recommendation_does_not_mutate_sources(fx):
    case_id = next(iter(fx.base.base.cases))
    before = fx.base.base.cs.registry.get(case_id).content_signature()
    fx.recommendations.build_context(scope="operational:recheck")
    after = fx.base.base.cs.registry.get(case_id).content_signature()
    assert before == after


def test_reports_are_versioned(fx):
    records = all_recommendations(fx)
    reports = fx.recommendations.reports(records)
    assert reports["guidance_report"]["recommendation_report_version"]
    assert reports["escalation_report"]["report_type"] == "recommendation_escalation"
    assert reports["priority_report"]["by_level"]
    assert reports["audit_report"]["verified"]
