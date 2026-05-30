"""Deterministic, explainable prioritization.

The review-priority score is a fixed weighted sum of normalized factors, so the
contribution of each factor is transparent (the contributions sum exactly to the
score). The score maps to a priority level by fixed thresholds. Nothing here is a
clinical decision: it only orders reviewer attention.
"""

from __future__ import annotations

from backend.decision_support.schemas.decision import (
    DecisionContext,
    PrioritizationRecord,
    PriorityFactor,
    PriorityLevel,
    RiskContext,
)
from backend.decision_support.schemas.decision import EvidenceBundle
from backend.multi_case_intelligence.schemas.determinism import quantize

# Fixed factor weights (sum to 1.0). Recorded here as the explainable policy.
WEIGHTS = {
    "risk": 0.40,
    "interpretation_incompleteness": 0.25,
    "review_incompleteness": 0.20,
    "finding_load": 0.15,
}
ELEVATED_THRESHOLD = 0.34
HIGH_THRESHOLD = 0.67
# Finding count that saturates the finding-load factor.
FINDING_LOAD_SATURATION = 5
# How many top-ranked evidence items to attach as supporting evidence.
TOP_EVIDENCE = 3


class Prioritizer:
    """Produces explainable :class:`PrioritizationRecord` artifacts."""

    def prioritize(
        self,
        context: DecisionContext,
        risk_context: RiskContext,
        evidence_bundle: EvidenceBundle,
        *,
        schema_version: str = "v2.p6.1",
    ) -> PrioritizationRecord:
        risk_value = risk_context.aggregate
        interp_incomplete = quantize(
            1.0 - context.completeness.get("interpretation_coverage", 0.0)
        )
        review_incomplete = quantize(
            1.0 - context.completeness.get("finalized_review_rate", 0.0)
        )
        finding_load = quantize(
            min(1.0, context.counts.get("findings", 0) / FINDING_LOAD_SATURATION)
        )

        values = {
            "risk": risk_value,
            "interpretation_incompleteness": interp_incomplete,
            "review_incompleteness": review_incomplete,
            "finding_load": finding_load,
        }
        factors = tuple(
            PriorityFactor(
                name=name,
                contribution=quantize(WEIGHTS[name] * values[name]),
                detail=f"weight={WEIGHTS[name]} x value={values[name]}",
            )
            for name in sorted(WEIGHTS)
        )
        score = quantize(sum(f.contribution for f in factors))
        level = self._level(score)
        reason = self._reason(level, factors)

        supporting_evidence = tuple(
            item.evidence_ref for item in evidence_bundle.items[:TOP_EVIDENCE]
        )
        priority_id = PrioritizationRecord.mint_id(context.id)
        return PrioritizationRecord(
            id=priority_id,
            schema_version=schema_version,
            context_ref=context.ref(),
            level=level,
            score=score,
            reason=reason,
            factors=factors,
            supporting_evidence=supporting_evidence,
            risk_context_ref=risk_context.ref(),
            knowledge_refs=context.knowledge_refs,
        )

    @staticmethod
    def _level(score: float) -> PriorityLevel:
        if score < ELEVATED_THRESHOLD:
            return PriorityLevel.ROUTINE
        if score < HIGH_THRESHOLD:
            return PriorityLevel.ELEVATED
        return PriorityLevel.HIGH

    @staticmethod
    def _reason(level: PriorityLevel, factors: tuple[PriorityFactor, ...]) -> str:
        ranked = sorted(factors, key=lambda f: (-f.contribution, f.name))
        top = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        drivers = ", ".join(
            f"{f.name} (+{f.contribution})" for f in (top, second) if f is not None
        )
        return (
            f"Review priority {level.value.upper()} driven primarily by {drivers}. "
            "This ranks reviewer attention only and is not a clinical decision."
        )
