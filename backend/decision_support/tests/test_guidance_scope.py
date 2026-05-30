"""Guidance generation and decision-scope guard tests (V2-P6).

These tests directly verify validation criterion #20: no recommendation exceeds
decision-support scope (no diagnosis/treatment/medication/clinical orders).
"""

from __future__ import annotations

from backend.decision_support.context.aggregator import ContextAggregator
from backend.decision_support.evidence.bundler import EvidenceBundler
from backend.decision_support.guidance.generator import GuidanceGenerator
from backend.decision_support.prioritization.prioritizer import Prioritizer
from backend.decision_support.risk.aggregator import RiskContextAggregator
from backend.decision_support.schemas.decision import (
    GuidanceCategory,
    GuidanceItem,
    GuidanceRecord,
)
from backend.decision_support.validation.validators import (
    DecisionGovernanceGate,
    DecisionScopeGuard,
)
from backend.multi_case_intelligence.schemas.base import ArtifactKind, ArtifactRef


def _guidance_for(pop, case_id):
    ctx = ContextAggregator().build_context(pop, case_id)
    risk = RiskContextAggregator().build_risk(pop, ctx)
    bundle = EvidenceBundler().build_bundle(pop, ctx)
    pr = Prioritizer().prioritize(ctx, risk, bundle)
    return ctx, GuidanceGenerator().generate(pop, ctx, risk, pr)


def test_guidance_covers_expected_categories(sample_population):
    # C3 has unfinalized review, missing interpretation, missing evidence,
    # uncovered knowledge, plus the always-present risk item.
    _, guidance = _guidance_for(sample_population, "C3")
    cats = {it.category for it in guidance.items}
    assert GuidanceCategory.REVIEW in cats
    assert GuidanceCategory.INVESTIGATION in cats
    assert GuidanceCategory.EVIDENCE in cats
    assert GuidanceCategory.KNOWLEDGE in cats
    assert GuidanceCategory.RISK in cats


def test_guidance_contains_no_clinical_directives(sample_population):
    guard = DecisionScopeGuard()
    for case_id in ("C1", "C2", "C3", "C4"):
        _, guidance = _guidance_for(sample_population, case_id)
        assert guard.scan_artifact(guidance) == ()


def test_guidance_is_deterministic(sample_population):
    _, g1 = _guidance_for(sample_population, "C3")
    _, g2 = _guidance_for(sample_population, "C3")
    assert g1.compute_hash() == g2.compute_hash()


def test_scope_guard_detects_forbidden_terms():
    guard = DecisionScopeGuard()
    found = guard.scan_text("Start treatment and prescribe medication for the diagnosis.")
    assert "treatment" in found
    assert "prescribe" in found
    assert "medication" in found
    assert "diagnosis" in found


def test_scope_guard_allows_process_language():
    guard = DecisionScopeGuard()
    assert guard.scan_text("Complete the review and attach evidence before sign-off.") == ()
    # "order" as in "in order to" must NOT trip the guard.
    assert guard.scan_text("Sort the queue in order to prioritize review attention.") == ()


def test_gate_rejects_guidance_with_clinical_directive():
    """A guidance record carrying out-of-scope language is refused by the gate."""
    ctx_ref = ArtifactRef(kind=ArtifactKind.DECISION_CONTEXT, id="dc-1", content_hash="h", version=1)
    bad = GuidanceRecord(
        id="guidance-bad",
        context_ref=ctx_ref,
        items=(
            GuidanceItem(
                category=GuidanceCategory.REVIEW,
                message="Begin treatment with the recommended medication.",
                rationale="(injected out-of-scope content)",
            ),
        ),
    )
    report = DecisionGovernanceGate().evaluate(bad, parents=(ctx_ref,))
    assert not report.passed
    assert "risk_validation" in {r.name for r in report.failures}
