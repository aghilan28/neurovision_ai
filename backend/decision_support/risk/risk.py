"""Deterministic risk-context aggregation (V2-P6).

Aggregates inference/coverage/calibration/finding/evidence/knowledge/review risk
for a case into an explainable :class:`RiskContext`. The V1 uncertainty components
are derived from the **recorded** ``evidence_confidence`` on findings (read, never
recomputed — AP-4/NR-4); the structural components come from V2 completeness. This
is decision-support *review-attention* risk — how much a human should look closely
— never a clinical risk score, diagnosis, or prognosis.
"""

from __future__ import annotations

from typing import Sequence

from backend.clinical_findings.models.domain import FindingStatus
from backend.clinical_review.models.domain import ReviewStatus
from backend.multi_case_intelligence.population import PopulationView, finding_confidence

from ..identity import mint_risk_context
from ..models.domain import DecisionContext, RiskBand, RiskComponent, RiskContext

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}
MODERATE_THRESHOLD = 0.34
ELEVATED_THRESHOLD = 0.67


def _round(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


def _mean(values: Sequence[float]) -> float:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


class RiskContextAggregator:
    """Builds :class:`RiskContext` artifacts for a case (read-only)."""

    def build(self, population: PopulationView, context: DecisionContext) -> RiskContext:
        case_id = context.case_id
        findings = population.findings_for_case(case_id)
        reviews = population.reviews_for_case(case_id)
        n = len(findings)

        # V1 uncertainty components from RECORDED evidence confidence per type.
        finding_confs = [finding_confidence(f) for f in findings]
        finding_confs = [c for c in finding_confs if c is not None]
        fallback_conf = _mean(finding_confs) if finding_confs else 0.0

        def type_conf(evidence_type: str) -> float:
            vals = [e.evidence_confidence for f in findings for e in f.evidence
                    if e.evidence_type == evidence_type and e.evidence_confidence is not None]
            return _mean(vals) if vals else fallback_conf

        inference_risk = _round(1.0 - type_conf("inference"))
        coverage_risk = _round(1.0 - type_conf("coverage"))
        calibration_risk = _round(1.0 - type_conf("calibration"))

        finding_risk = _round(
            sum(1 for f in findings if f.status != FindingStatus.CONFIRMED) / n) if n else 0.0
        evidence_risk = _round(
            sum(1 for f in findings if len(f.evidence) < 2) / n) if n else 0.0
        categories = {f.record.category for f in findings}
        unknown = {c for c in categories if not population.category_is_known(c)}
        knowledge_risk = _round(len(unknown) / len(categories)) if categories else 0.0
        review_risk = (1.0 if not any(r.status in _FINALIZED_REVIEW for r in reviews)
                       else _round(sum(1 for r in reviews if r.status not in _FINALIZED_REVIEW) / len(reviews)))

        components = (
            RiskComponent("inference_risk", inference_risk,
                          "1 - mean recorded inference confidence (V1 inference uncertainty)."),
            RiskComponent("coverage_risk", coverage_risk,
                          "1 - mean recorded coverage confidence (V1 conformal coverage)."),
            RiskComponent("calibration_risk", calibration_risk,
                          "1 - mean recorded calibration confidence (V1 calibration)."),
            RiskComponent("finding_risk", finding_risk,
                          "Fraction of findings not yet CONFIRMED."),
            RiskComponent("evidence_risk", evidence_risk,
                          "Fraction of findings with fewer than two evidence items."),
            RiskComponent("knowledge_risk", knowledge_risk,
                          "Fraction of finding categories absent from the knowledge vocabulary."),
            RiskComponent("review_risk", review_risk,
                          "Fraction of reviews not finalized (1.0 if none finalized)."),
        )
        aggregate = _round(sum(c.value for c in components) / len(components))
        band = (RiskBand.LOW if aggregate < MODERATE_THRESHOLD
                else RiskBand.MODERATE if aggregate < ELEVATED_THRESHOLD else RiskBand.ELEVATED)
        ident = mint_risk_context(context.context_id)
        return RiskContext(risk_id=ident.id, context_id=context.context_id,
                           components=components, aggregate=aggregate, band=band)
