"""Deterministic risk-context aggregation.

Builds the seven mandated risk components from the V1 uncertainty signals and the
V2 completeness of the case context. Every component carries a human-readable
basis, and the aggregate band is derived with fixed thresholds, so the result is
explainable and reproducible.
"""

from __future__ import annotations

from typing import Sequence

from backend.decision_support.schemas.decision import (
    DecisionContext,
    RiskBand,
    RiskComponent,
    RiskContext,
)
from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.determinism import quantize
from backend.multi_case_intelligence.schemas.source import Finding

# Confidence below this marks a finding as needing closer review.
LOW_CONFIDENCE = 0.5
# Aggregate band thresholds.
MODERATE_THRESHOLD = 0.34
ELEVATED_THRESHOLD = 0.67


def _mean(values: Sequence[float]) -> float:
    return quantize(sum(values) / len(values)) if values else 0.0


class RiskContextAggregator:
    """Builds :class:`RiskContext` artifacts for a decision context (read-only)."""

    def build_risk(
        self,
        population: SourcePopulation,
        context: DecisionContext,
        *,
        schema_version: str = "v2.p6.1",
    ) -> RiskContext:
        case_id = context.case_ref.id
        findings = population.findings_for_case(case_id)
        reviews = population.reviews_for_case(case_id)

        inf_vals = [self._inference_risk(f) for f in findings]
        cov_vals = [self._coverage_risk(f) for f in findings]
        cal_vals = [self._calibration_risk(f) for f in findings]

        n = len(findings)
        finding_risk = (
            quantize(
                sum(
                    1
                    for f in findings
                    if (f.signal is not None and f.signal.abstained)
                    or (f.signal is not None and f.signal.confidence < LOW_CONFIDENCE)
                )
                / n
            )
            if n
            else 0.0
        )
        evidence_risk = (
            quantize(sum(1 for f in findings if not f.evidence_ids) / n) if n else 0.0
        )

        categories = {f.category for f in findings}
        knowledge_categories = {
            k.finding_category for k in population.knowledge if k.finding_category is not None
        }
        missing = categories - knowledge_categories
        knowledge_risk = quantize(len(missing) / len(categories)) if categories else 0.0

        review_risk = (
            quantize(sum(1 for r in reviews if not r.is_finalized) / len(reviews))
            if reviews
            else 1.0
        )

        components = (
            RiskComponent("inference_risk", _mean(inf_vals), "Mean finding inference risk (V1 inference uncertainty)."),
            RiskComponent("coverage_risk", _mean(cov_vals), "Mean finding coverage risk (V1 conformal coverage gap)."),
            RiskComponent("calibration_risk", _mean(cal_vals), "Mean finding calibration risk (V1 calibration error)."),
            RiskComponent("finding_risk", finding_risk, "Fraction of findings abstained or below confidence threshold."),
            RiskComponent("evidence_risk", evidence_risk, "Fraction of findings lacking supporting evidence."),
            RiskComponent("knowledge_risk", knowledge_risk, "Fraction of finding categories lacking linked knowledge."),
            RiskComponent("review_risk", review_risk, "Fraction of reviews not finalized (or no review yet)."),
        )
        aggregate = _mean([c.value for c in components])
        band = self._band(aggregate)

        risk_id = RiskContext.mint_id(context.id)
        return RiskContext(
            id=risk_id,
            schema_version=schema_version,
            context_ref=context.ref(),
            components=components,
            aggregate=aggregate,
            band=band,
        )

    @staticmethod
    def _inference_risk(f: Finding) -> float:
        if f.risk is not None:
            return f.risk.inference_risk
        if f.signal is not None:
            return quantize(1.0 - f.signal.confidence)
        return 0.0

    @staticmethod
    def _coverage_risk(f: Finding) -> float:
        if f.risk is not None:
            return f.risk.coverage_risk
        if f.signal is not None:
            return quantize(max(0.0, f.signal.coverage_target - f.signal.empirical_coverage))
        return 0.0

    @staticmethod
    def _calibration_risk(f: Finding) -> float:
        if f.risk is not None:
            return f.risk.calibration_risk
        if f.signal is not None:
            return f.signal.calibration_error
        return 0.0

    @staticmethod
    def _band(aggregate: float) -> RiskBand:
        if aggregate < MODERATE_THRESHOLD:
            return RiskBand.LOW
        if aggregate < ELEVATED_THRESHOLD:
            return RiskBand.MODERATE
        return RiskBand.ELEVATED
