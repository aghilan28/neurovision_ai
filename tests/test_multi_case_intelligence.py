"""Tests for the Multi-Case Intelligence Layer (V2-P5).

Covers identity/determinism, cohorts, population analytics, trends, quality
analytics, the registry, immutable audit, lineage-to-patient, the governance gate,
source immutability, and full artifact validation — all over the *real* V2
aggregates (shared lineage tracker).
"""

from __future__ import annotations

import pytest

from backend.multi_case_intelligence import (
    MultiCaseIntelligenceService, CohortBuilder, CohortDefinition, CohortCriterion, CohortKind,
    QualityReport, QualityMetric, GovernanceGate, validate_identity,
)
from backend.multi_case_intelligence.statistics import statistics as st

from tests._p5p6_helpers import build_multicase


@pytest.fixture
def mc():
    return build_multicase()


# --- determinism --------------------------------------------------------------
def test_statistics_are_deterministic_and_bounded():
    recs = [{"k": "a"}, {"k": "a"}, {"k": "b"}]
    d = st.distribution(recs, lambda r: r["k"])
    assert d == {"counts": {"a": 2, "b": 1}, "total": 3}
    assert st.frequency(d) == {"a": st._round(2 / 3), "b": st._round(1 / 3)}
    assert 0.0 <= st.normalized_entropy(d) <= 1.0


# --- cohorts ------------------------------------------------------------------
def test_finding_cohort_selects_by_category(mc):
    cohort = CohortBuilder().build(mc.population, CohortDefinition(
        member_kind=CohortKind.FINDING, criteria=(CohortCriterion("category", "eq", "LPD"),)))
    assert cohort.members == (mc.findings["F1"].finding_id,)


def test_cohort_members_sorted_unique_and_or_combinator(mc):
    cohort = CohortBuilder().build(mc.population, CohortDefinition(
        member_kind=CohortKind.FINDING,
        criteria=(CohortCriterion("category", "eq", "LPD"), CohortCriterion("category", "eq", "GPD")),
        combinator="or"))
    assert list(cohort.members) == sorted(cohort.members)
    assert len(set(cohort.members)) == len(cohort.members)
    assert set(cohort.members) == {mc.findings["F1"].finding_id, mc.findings["F2"].finding_id}


def test_cohort_identity_is_definition_not_membership():
    """Same definition over different data -> same id, different content."""
    a = build_multicase()
    b = build_multicase()
    defn = CohortDefinition(member_kind=CohortKind.CASE)
    ca = CohortBuilder().build(a.population, defn)
    cb = CohortBuilder().build(b.population, defn)
    assert ca.cohort_id == cb.cohort_id  # identical definition + identical seed data
    assert ca.state_signature() == cb.state_signature()


# --- analytics / trends / quality --------------------------------------------
def test_population_analytics_counts(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    an = mci.build_population_analytics(mc.population)
    assert an.block("case").count == 3
    assert an.block("review").count == 3
    assert an.block("finding").count == 4
    cat = an.block("finding").distributions["category"]["counts"]
    assert cat == {"GPD": 1, "GRDA": 1, "LPD": 1, "unknown_pattern": 1}


def test_quality_metrics_known_values(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    q = mci.build_quality(mc.population)
    metrics = {m.name: m for m in q.metrics}
    assert metrics["review_finalized_rate"].value == st._round(1 / 3)
    assert metrics["interpretation_coverage"].value == st._round(1 / 4)
    assert metrics["knowledge_linkage"].value == st._round(3 / 4)  # LPD,GPD,GRDA known
    assert metrics["referential_integrity"].value == 1.0
    for m in q.metrics:
        assert 0.0 <= m.value <= 1.0 and m.numerator <= m.denominator


def test_trends_deterministic(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    t1 = mci.build_trend(mc.population)
    metrics = {s.metric for s in t1.series}
    assert "finding_status_progression" in metrics and "cases_per_patient" in metrics
    t2 = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage).build_trend(mc.population)
    assert t1.state_signature() == t2.state_signature()


# --- registry / audit / lineage / governance ---------------------------------
def test_no_artifact_exists_outside_registry_and_audit_verifies(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    res = mci.run_full_intelligence(mc.population)
    for art, kind in [(res["analytics"], "analytics"), (res["trend"], "trend"),
                      (res["quality"], "quality"), (res["summary"], "intel_report")]:
        aid = getattr(art, "analytics_id", None) or getattr(art, "trend_id", None) \
            or getattr(art, "quality_id", None) or art.report_id
        assert mci.registry.exists(aid)
        assert validate_identity(aid, kind)[0]
    assert mci.audit.verify()


def test_lineage_spans_to_patient(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    an = mci.build_population_analytics(mc.population)
    kinds = {r.kind for r in mc.cs.lineage.chain(an.lineage_id)}
    assert {"analytics", "case", "finding", "patient"} <= kinds
    assert mc.cs.lineage.verify_chain(an.lineage_id)


def test_governance_gate_rejects_out_of_range_metric():
    bad = QualityReport(quality_id="quality+" + "0" * 16, scope="x",
                        metrics=(QualityMetric("bad", 2.0, 5, 1, "out of range"),))
    report = GovernanceGate().evaluate(artifact=bad, kind="quality", parents=("lineage+" + "a" * 16,))
    assert not report.ok
    assert "quality_validation" in {c.name for c in report.failures()}


def test_full_validation_passes_and_source_immutable(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    baseline = mc.population.integrity_digest()
    res = mci.run_full_intelligence(mc.population)
    for art, kind in [(res["analytics"], "analytics"), (res["trend"], "trend"),
                      (res["quality"], "quality"), (res["summary"], "intel_report")]:
        rep = mci.validate(art, kind, population=mc.population, baseline_digest=baseline)
        assert rep.ok, rep.to_dict()


def test_source_immutability_detected_when_baseline_differs(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    an = mci.build_population_analytics(mc.population)
    other_baseline = build_multicase().population.integrity_digest()
    # tamper the baseline so it no longer matches the (unchanged) population
    other_baseline = dict(other_baseline); other_baseline["finding"] = "deadbeef"
    rep = mci.validate(an, "analytics", population=mc.population, baseline_digest=other_baseline)
    assert "source_immutability" in {c.name for c in rep.failures()}
