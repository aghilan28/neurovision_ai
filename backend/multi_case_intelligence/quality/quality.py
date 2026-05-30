"""Deterministic quality analytics (V2-P5).

Produces a :class:`QualityReport` of explainable ratio metrics. Every metric
carries its numerator and denominator so it is transparent and reproducible.
"""

from __future__ import annotations

from backend.clinical_findings.models.domain import FindingStatus
from backend.clinical_review.models.domain import ReviewStatus

from ..identity import mint_quality
from ..models.domain import QualityMetric, QualityReport
from ..population import PopulationView, finding_confidence

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}


def _metric(name: str, num: int, den: int, description: str) -> QualityMetric:
    value = round(num / den, 6) if den else 0.0
    return QualityMetric(name=name, value=value, numerator=int(num), denominator=int(den),
                         description=description)


class QualityAnalyzer:
    """Computes quality intelligence over a population (read-only)."""

    def analyze(self, population: PopulationView, *, scope: str = "population") -> QualityReport:
        metrics = (
            self._review_finalized_rate(population),
            self._finding_confirmed_rate(population),
            self._interpretation_coverage(population),
            self._multi_evidence_rate(population),
            self._recorded_confidence_coverage(population),
            self._knowledge_linkage(population),
            self._referential_integrity(population),
        )
        ident = mint_quality(scope)
        return QualityReport(quality_id=ident.id, scope=scope, metrics=metrics)

    def _review_finalized_rate(self, p: PopulationView) -> QualityMetric:
        n = sum(1 for r in p.reviews if r.status in _FINALIZED_REVIEW)
        return _metric("review_finalized_rate", n, len(p.reviews),
                       "Fraction of reviews finalized (completed/closed/archived).")

    def _finding_confirmed_rate(self, p: PopulationView) -> QualityMetric:
        n = sum(1 for f in p.findings if f.status == FindingStatus.CONFIRMED)
        return _metric("finding_confirmed_rate", n, len(p.findings),
                       "Fraction of findings in the CONFIRMED state.")

    def _interpretation_coverage(self, p: PopulationView) -> QualityMetric:
        n = sum(1 for f in p.findings if len(f.interpretation_ids) > 0)
        return _metric("interpretation_coverage", n, len(p.findings),
                       "Fraction of findings with at least one interpretation.")

    def _multi_evidence_rate(self, p: PopulationView) -> QualityMetric:
        n = sum(1 for f in p.findings if len(f.evidence) >= 2)
        return _metric("multi_evidence_rate", n, len(p.findings),
                       "Fraction of findings backed by two or more evidence items.")

    def _recorded_confidence_coverage(self, p: PopulationView) -> QualityMetric:
        n = sum(1 for f in p.findings if finding_confidence(f) is not None)
        return _metric("recorded_confidence_coverage", n, len(p.findings),
                       "Fraction of findings carrying a recorded (V1) confidence.")

    def _knowledge_linkage(self, p: PopulationView) -> QualityMetric:
        categories = {f.record.category for f in p.findings}
        known = {c for c in categories if p.category_is_known(c)}
        return _metric("knowledge_linkage", len(known), len(categories),
                       "Fraction of finding categories present in the knowledge vocabulary.")

    def _referential_integrity(self, p: PopulationView) -> QualityMetric:
        case_ids = {c.case_id for c in p.cases}
        review_ids = {r.review_id for r in p.reviews}
        finding_ids = {f.finding_id for f in p.findings}
        total = 0
        ok = 0
        for f in p.findings:
            total += 2
            ok += int(f.case_id in case_ids) + int(f.review_id in review_ids)
        for i in p.interpretations:
            total += 1
            ok += int(i.finding_id in finding_ids)
        return _metric("referential_integrity", ok, total,
                       "Fraction of source cross-references (finding/interpretation) that resolve.")
