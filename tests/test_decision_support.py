"""Tests for the Decision Support Layer (V2-P6).

Covers context aggregation, evidence bundling (nothing hidden), the explainable
risk context and prioritization, process-only guidance, the decision scope guard
(directive criterion: no recommendation exceeds decision-support scope), the
registry/audit/lineage, and full artifact validation — over the real V2 aggregates.
"""

from __future__ import annotations

import pytest

from backend.multi_case_intelligence import MultiCaseIntelligenceService
from backend.decision_support import (
    DecisionSupportService, DecisionScopeGuard, DecisionGovernanceGate,
    GuidanceRecord, GuidanceItem, GuidanceCategory, RiskBand, validate_identity,
)

from tests._p5p6_helpers import build_multicase


@pytest.fixture
def mc():
    return build_multicase()


# --- context ------------------------------------------------------------------
def test_context_aggregates_case(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ctx = ds.build_context(mc.population, mc.cases["C1"].case_id)
    assert ctx.counts["findings"] == 2
    assert ctx.counts["reviews"] == 1
    assert ctx.completeness["finalized_review_rate"] == 1.0
    assert ctx.completeness["interpretation_coverage"] == 0.5  # F1 interp, F2 none


def test_context_embeds_population_context(mc):
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    an = mci.build_population_analytics(mc.population)
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ctx = ds.build_context(mc.population, mc.cases["C1"].case_id, population_analytics=an)
    assert ctx.population_context.get("analytics_id") == an.analytics_id
    assert "category_frequency" in ctx.population_context


def test_context_unknown_case_raises(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    with pytest.raises(KeyError):
        ds.build_context(mc.population, "case+" + "0" * 16)


# --- evidence bundling --------------------------------------------------------
def test_evidence_bundle_includes_all_and_ranks(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ctx = ds.build_context(mc.population, mc.cases["C1"].case_id)
    bundle = ds.build_evidence_bundle(mc.population, ctx)
    # F1 has 2 evidence, F2 has 1 -> 3 total, none hidden.
    assert bundle.size == 3
    assert set(bundle.ranking) == set(ctx.evidence_ids)
    confs = [it.confidence for it in bundle.items]
    assert confs == sorted(confs, reverse=True)  # ranked by recorded confidence desc
    assert [it.rank for it in bundle.items] == [1, 2, 3]


# --- risk context -------------------------------------------------------------
def test_risk_components_and_aggregate(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ctx = ds.build_context(mc.population, mc.cases["C2"].case_id)  # low-confidence, in-progress
    risk = ds.build_risk_context(mc.population, ctx)
    names = {c.name for c in risk.components}
    assert names == {"inference_risk", "coverage_risk", "calibration_risk", "finding_risk",
                     "evidence_risk", "knowledge_risk", "review_risk"}
    # inference risk reads recorded confidence (0.3) -> 0.7
    assert risk.component("inference_risk").value == 0.7
    assert risk.component("review_risk").value == 1.0  # in-progress, none finalized
    mean = round(sum(c.value for c in risk.components) / len(risk.components), 6)
    assert abs(mean - risk.aggregate) < 1e-9
    assert risk.band in (RiskBand.LOW, RiskBand.MODERATE, RiskBand.ELEVATED)


# --- prioritization -----------------------------------------------------------
def test_prioritization_contributions_sum_to_score(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ctx = ds.build_context(mc.population, mc.cases["C2"].case_id)
    risk = ds.build_risk_context(mc.population, ctx)
    bundle = ds.build_evidence_bundle(mc.population, ctx)
    pr = ds.build_prioritization(ctx, risk, bundle)
    total = round(sum(f.contribution for f in pr.factors), 6)
    assert abs(total - pr.score) < 1e-9
    assert {f.name for f in pr.factors} == {"risk", "interpretation_incompleteness",
                                            "review_incompleteness", "finding_load"}


# --- guidance + scope guard ---------------------------------------------------
def test_guidance_is_process_only_and_scope_clean(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    guard = DecisionScopeGuard()
    for cid in (mc.cases["C1"].case_id, mc.cases["C2"].case_id, mc.cases["C3"].case_id):
        bundle = ds.process_case(mc.population, cid)
        assert guard.scan_artifact(bundle.guidance) == ()
        cats = {it.category.value for it in bundle.guidance.items}
        assert "risk" in cats  # risk guidance always present


def test_scope_guard_detects_clinical_directives():
    guard = DecisionScopeGuard()
    found = guard.scan_text("Start treatment and prescribe medication for the diagnosis.")
    assert {"treatment", "prescribe", "medication", "diagnosis"} <= set(found)
    # process language and the ambiguous word 'order' must NOT trip the guard
    assert guard.scan_text("Complete the review in order to attach evidence.") == ()


def test_gate_rejects_guidance_with_clinical_directive():
    ctx_ref = "decision_context+" + "0" * 16
    bad = GuidanceRecord(guidance_id="guidance+" + "0" * 16, context_id=ctx_ref,
                         items=(GuidanceItem(category=GuidanceCategory.REVIEW,
                                             message="Begin treatment with the recommended medication.",
                                             rationale="(injected)"),))
    report = DecisionGovernanceGate().evaluate(artifact=bad, kind="guidance",
                                               parents=("lineage+" + "a" * 16,))
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}


# --- full validation + lineage ------------------------------------------------
def test_full_decision_validation_passes(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    baseline = mc.population.integrity_digest()
    bundle = ds.process_case(mc.population, mc.cases["C1"].case_id)
    kinds = ["decision_context", "evidence_bundle", "risk_context", "prioritization",
             "guidance", "decision_support"]
    for art, kind in zip(bundle.artifacts(), kinds):
        rep = ds.validate(art, kind, population=mc.population, baseline_digest=baseline)
        assert rep.ok, rep.to_dict()
        assert "decision_scope_integrity" in {c.name for c in rep.checks}
    assert ds.audit.verify()


def test_decision_lineage_traces_to_patient(mc):
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    bundle = ds.process_case(mc.population, mc.cases["C1"].case_id)
    kinds = {r.kind for r in mc.cs.lineage.chain(bundle.decision_support.lineage_id)}
    assert {"decision_support", "decision_context", "guidance", "finding", "case", "patient"} <= kinds
    assert validate_identity(bundle.decision_support.record_id, "decision_support")[0]


def test_decision_support_is_reproducible():
    a = build_multicase(); b = build_multicase()
    da = DecisionSupportService(lineage_tracker=a.cs.lineage).process_case(a.population, a.cases["C1"].case_id)
    db = DecisionSupportService(lineage_tracker=b.cs.lineage).process_case(b.population, b.cases["C1"].case_id)
    assert da.decision_support.state_signature() == db.decision_support.state_signature()
    assert da.decision_support.version == db.decision_support.version
