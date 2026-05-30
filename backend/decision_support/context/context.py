"""Deterministic decision-context aggregation (V2-P6).

Given a case, the aggregator collects every related source id (reviews, findings,
interpretations, evidence, linked knowledge concepts) from the immutable
population and packages references + derived completeness/counts into a
:class:`DecisionContext`. It optionally embeds population context (by value) from a
V2-P5 ``PopulationAnalytics`` artifact. It never mutates source records.
"""

from __future__ import annotations


from backend.clinical_review.models.domain import ReviewStatus
from backend.multi_case_intelligence.population import PopulationView, finding_confidence

from ..identity import mint_context
from ..models.domain import DecisionContext

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}


def _round(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


class ContextAggregator:
    """Builds :class:`DecisionContext` bundles from a population (read-only)."""

    def build(self, population: PopulationView, case_id: str, *,
              population_analytics=None) -> DecisionContext:
        case = population.case(case_id)
        if case is None:
            raise KeyError(f"case {case_id!r} not in population")
        reviews = population.reviews_for_case(case_id)
        findings = population.findings_for_case(case_id)
        interpretations = tuple(
            i for f in findings for i in population.interpretations_for_finding(f.finding_id))
        evidence_ids = tuple(sorted({e.evidence_id for f in findings for e in f.evidence}))
        categories = {f.record.category for f in findings}
        concept_ids = tuple(sorted(
            c.concept_id for c in population.concepts
            if c.name.lower() in {x.lower() for x in categories}
            or categories & {rt for rt in c.related_terms}))

        n_findings = len(findings)
        completeness = {
            "interpretation_coverage": _round(
                sum(1 for f in findings if f.interpretation_ids) / n_findings) if n_findings else 0.0,
            "finalized_review_rate": _round(
                sum(1 for r in reviews if r.status in _FINALIZED_REVIEW) / len(reviews)) if reviews else 0.0,
            "multi_evidence_rate": _round(
                sum(1 for f in findings if len(f.evidence) >= 2) / n_findings) if n_findings else 0.0,
            "known_category_rate": _round(
                sum(1 for f in findings if population.category_is_known(f.record.category)) / n_findings)
            if n_findings else 0.0,
            "recorded_confidence_rate": _round(
                sum(1 for f in findings if finding_confidence(f) is not None) / n_findings)
            if n_findings else 0.0,
        }
        counts = {"reviews": len(reviews), "findings": n_findings,
                  "interpretations": len(interpretations), "evidence": len(evidence_ids),
                  "concepts": len(concept_ids)}

        ident = mint_context(case_id)
        return DecisionContext(
            context_id=ident.id, case_id=case_id, patient_id=case.patient_id,
            review_ids=tuple(r.review_id for r in reviews),
            finding_ids=tuple(f.finding_id for f in findings),
            interpretation_ids=tuple(i.interpretation_id for i in interpretations),
            evidence_ids=evidence_ids, concept_ids=concept_ids,
            completeness=completeness, counts=counts,
            population_context=self._population_context(population_analytics, categories))

    def _population_context(self, analytics, categories) -> dict:
        if analytics is None:
            return {}
        block = analytics.block("finding") if hasattr(analytics, "block") else None
        if block is None:
            return {"analytics_id": getattr(analytics, "analytics_id", None)}
        freq = block.frequency
        return {"analytics_id": analytics.analytics_id, "population_finding_count": block.count,
                "category_frequency": {c: freq.get(c, 0.0) for c in sorted(categories)}}
