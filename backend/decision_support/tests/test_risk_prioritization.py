"""Risk context and prioritization tests (V2-P6)."""

from __future__ import annotations

from backend.decision_support.context.aggregator import ContextAggregator
from backend.decision_support.evidence.bundler import EvidenceBundler
from backend.decision_support.prioritization.prioritizer import Prioritizer
from backend.decision_support.risk.aggregator import RiskContextAggregator
from backend.decision_support.schemas.decision import PriorityLevel, RiskBand


def _risk_for(pop, case_id):
    ctx = ContextAggregator().build_context(pop, case_id)
    return ctx, RiskContextAggregator().build_risk(pop, ctx)


# -- risk ------------------------------------------------------------------ #
def test_risk_components_present_and_in_range(sample_population):
    _, risk = _risk_for(sample_population, "C3")
    names = {c.name for c in risk.components}
    assert names == {
        "inference_risk",
        "coverage_risk",
        "calibration_risk",
        "finding_risk",
        "evidence_risk",
        "knowledge_risk",
        "review_risk",
    }
    for c in risk.components:
        assert 0.0 <= c.value <= 1.0


def test_risk_aggregate_is_mean_of_components(sample_population):
    _, risk = _risk_for(sample_population, "C3")
    mean = round(sum(c.value for c in risk.components) / len(risk.components), 9)
    assert abs(mean - risk.aggregate) < 1e-9


def test_high_risk_case_is_elevated(sample_population):
    # C3: abstained low-confidence finding, no evidence, no interpretation,
    # uncovered category (LPD), pending review -> elevated band.
    _, risk = _risk_for(sample_population, "C3")
    assert risk.component("evidence_risk").value == 1.0
    assert risk.component("knowledge_risk").value == 1.0
    assert risk.component("review_risk").value == 1.0
    assert risk.band == RiskBand.ELEVATED


def test_low_risk_case_is_lower_band(sample_population):
    # C1: finalized review, both findings have evidence, interpretations present,
    # categories covered -> lower aggregate than C3.
    _, risk_c1 = _risk_for(sample_population, "C1")
    _, risk_c3 = _risk_for(sample_population, "C3")
    assert risk_c1.aggregate < risk_c3.aggregate


def test_risk_is_deterministic(sample_population):
    _, r1 = _risk_for(sample_population, "C3")
    _, r2 = _risk_for(sample_population, "C3")
    assert r1.compute_hash() == r2.compute_hash()


# -- prioritization -------------------------------------------------------- #
def test_prioritization_contributions_sum_to_score(sample_population):
    ctx, risk = _risk_for(sample_population, "C3")
    bundle = EvidenceBundler().build_bundle(sample_population, ctx)
    pr = Prioritizer().prioritize(ctx, risk, bundle)
    total = round(sum(f.contribution for f in pr.factors), 9)
    assert abs(total - pr.score) < 1e-9
    assert 0.0 <= pr.score <= 1.0


def test_prioritization_levels(sample_population):
    # C3 is incomplete + high risk -> HIGH; C1 is complete + low risk -> lower.
    ctx3, risk3 = _risk_for(sample_population, "C3")
    b3 = EvidenceBundler().build_bundle(sample_population, ctx3)
    pr3 = Prioritizer().prioritize(ctx3, risk3, b3)
    assert pr3.level == PriorityLevel.HIGH

    ctx1, risk1 = _risk_for(sample_population, "C1")
    b1 = EvidenceBundler().build_bundle(sample_population, ctx1)
    pr1 = Prioritizer().prioritize(ctx1, risk1, b1)
    assert pr1.score < pr3.score


def test_prioritization_is_explainable(sample_population):
    ctx, risk = _risk_for(sample_population, "C3")
    bundle = EvidenceBundler().build_bundle(sample_population, ctx)
    pr = Prioritizer().prioritize(ctx, risk, bundle)
    factor_names = {f.name for f in pr.factors}
    assert factor_names == {
        "risk",
        "interpretation_incompleteness",
        "review_incompleteness",
        "finding_load",
    }
    assert pr.reason
    assert pr.risk_context_ref == risk.ref()
