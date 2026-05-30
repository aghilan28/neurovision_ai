"""Deterministic quality analytics.

Produces a :class:`QualityReport` of explainable ratio metrics. Every metric
carries its numerator and denominator so it is transparent and reproducible.
"""

from __future__ import annotations

from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.determinism import quantize
from backend.multi_case_intelligence.schemas.intelligence import QualityMetric, QualityReport


def _metric(name: str, numerator: int, denominator: int, description: str) -> QualityMetric:
    value = quantize(numerator / denominator) if denominator else 0.0
    return QualityMetric(
        name=name, value=value, numerator=numerator, denominator=denominator, description=description
    )


class QualityAnalyzer:
    """Computes quality intelligence over a source population (read-only)."""

    def analyze(
        self, population: SourcePopulation, *, scope: str = "population", schema_version: str = "v2.p5.1"
    ) -> QualityReport:
        metrics = (
            self._review_quality(population),
            self._finding_quality(population),
            self._evidence_completeness(population),
            self._interpretation_completeness(population),
            self._knowledge_coverage(population),
            self._referential_integrity(population),
        )
        report_id = QualityReport.mint_id(scope)
        return QualityReport(id=report_id, schema_version=schema_version, scope=scope, metrics=metrics)

    # -- metrics ----------------------------------------------------------- #
    def _review_quality(self, population: SourcePopulation) -> QualityMetric:
        reviews = population.reviews
        finalized = sum(1 for r in reviews if r.is_finalized)
        return _metric(
            "review_quality", finalized, len(reviews), "Fraction of reviews finalized (completed or signed-off)."
        )

    def _finding_quality(self, population: SourcePopulation) -> QualityMetric:
        findings = population.findings
        good = sum(
            1
            for f in findings
            if f.evidence_ids and population.interpretations_for_finding(f.finding_id)
        )
        return _metric(
            "finding_quality", good, len(findings),
            "Fraction of findings with at least one evidence item and one interpretation.",
        )

    def _evidence_completeness(self, population: SourcePopulation) -> QualityMetric:
        findings = population.findings
        with_ev = sum(1 for f in findings if f.evidence_ids)
        return _metric(
            "evidence_completeness", with_ev, len(findings),
            "Fraction of findings backed by at least one evidence item.",
        )

    def _interpretation_completeness(self, population: SourcePopulation) -> QualityMetric:
        findings = population.findings
        with_interp = sum(
            1 for f in findings if population.interpretations_for_finding(f.finding_id)
        )
        return _metric(
            "interpretation_completeness", with_interp, len(findings),
            "Fraction of findings with at least one interpretation.",
        )

    def _knowledge_coverage(self, population: SourcePopulation) -> QualityMetric:
        finding_categories = {f.category for f in population.findings}
        knowledge_categories = {
            k.finding_category for k in population.knowledge if k.finding_category is not None
        }
        covered = len(finding_categories & knowledge_categories)
        return _metric(
            "knowledge_coverage", covered, len(finding_categories),
            "Fraction of finding categories that have at least one knowledge artifact.",
        )

    def _referential_integrity(self, population: SourcePopulation) -> QualityMetric:
        """Fraction of cross-references between source artifacts that resolve.

        This is the population-level analogue of registry integrity: it proves
        the relational fabric (finding->review/case, evidence->finding,
        interpretation->finding) is intact.
        """
        total = 0
        resolved = 0
        case_ids = {c.case_id for c in population.cases}
        review_ids = {r.review_id for r in population.reviews}
        finding_ids = {f.finding_id for f in population.findings}

        for f in population.findings:
            total += 2
            resolved += int(f.review_id in review_ids) + int(f.case_id in case_ids)
        for e in population.evidence:
            if e.finding_id is not None:
                total += 1
                resolved += int(e.finding_id in finding_ids)
        for i in population.interpretations:
            total += 1
            resolved += int(i.finding_id in finding_ids)

        return _metric(
            "referential_integrity", resolved, total,
            "Fraction of source cross-references (finding/evidence/interpretation) that resolve.",
        )
