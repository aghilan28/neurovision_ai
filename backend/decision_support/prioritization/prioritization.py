"""Deterministic, explainable prioritization (V2-P6).

The review-priority score is a fixed weighted sum of normalized factors (risk,
interpretation/review incompleteness, finding load). The per-factor contributions
sum exactly to the score, and a human-readable reason names the top drivers. This
only orders reviewer attention; it is not clinical triage, diagnosis, or treatment.
"""

from __future__ import annotations

from ..identity import mint_prioritization
from ..models.domain import (
    DecisionContext, EvidenceBundle, PrioritizationRecord, PriorityFactor, PriorityLevel, RiskContext,
)

WEIGHTS = {"risk": 0.40, "interpretation_incompleteness": 0.25,
           "review_incompleteness": 0.20, "finding_load": 0.15}
ELEVATED_THRESHOLD = 0.34
HIGH_THRESHOLD = 0.67
FINDING_LOAD_SATURATION = 5
TOP_EVIDENCE = 3


def _round(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


class Prioritizer:
    """Produces explainable :class:`PrioritizationRecord` artifacts."""

    def build(self, context: DecisionContext, risk_context: RiskContext,
              evidence_bundle: EvidenceBundle) -> PrioritizationRecord:
        values = {
            "risk": risk_context.aggregate,
            "interpretation_incompleteness": _round(
                1.0 - context.completeness.get("interpretation_coverage", 0.0)),
            "review_incompleteness": _round(
                1.0 - context.completeness.get("finalized_review_rate", 0.0)),
            "finding_load": _round(min(1.0, context.counts.get("findings", 0) / FINDING_LOAD_SATURATION)),
        }
        factors = tuple(
            PriorityFactor(name=name, contribution=_round(WEIGHTS[name] * values[name]),
                           detail=f"weight={WEIGHTS[name]} x value={values[name]}")
            for name in sorted(WEIGHTS))
        score = _round(sum(f.contribution for f in factors))
        level = (PriorityLevel.ROUTINE if score < ELEVATED_THRESHOLD
                 else PriorityLevel.ELEVATED if score < HIGH_THRESHOLD else PriorityLevel.HIGH)
        reason = self._reason(level, factors)
        supporting = tuple(it.evidence_id for it in evidence_bundle.items[:TOP_EVIDENCE])
        ident = mint_prioritization(context.context_id)
        return PrioritizationRecord(
            priority_id=ident.id, context_id=context.context_id, level=level, score=score,
            reason=reason, factors=factors, supporting_evidence=supporting,
            risk_id=risk_context.risk_id)

    @staticmethod
    def _reason(level: PriorityLevel, factors: tuple) -> str:
        ranked = sorted(factors, key=lambda f: (-f.contribution, f.name))
        drivers = ", ".join(f"{f.name} (+{f.contribution})" for f in ranked[:2])
        return (f"Review priority {level.value.upper()} driven primarily by {drivers}. "
                "This ranks reviewer attention only and is not a clinical decision.")
