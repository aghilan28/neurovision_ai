"""Deterministic decision-context aggregation.

Given a case, the aggregator collects every related source artifact (reviews,
findings, interpretations, evidence, knowledge) from the immutable population and
packages references + derived completeness/counts into a
:class:`DecisionContext`. It optionally embeds population context (by value) from
a V2-P5 :class:`PopulationAnalytics` artifact. It never mutates source records.
"""

from __future__ import annotations

from backend.decision_support.schemas.decision import DecisionContext
from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.determinism import quantize
from backend.multi_case_intelligence.schemas.intelligence import PopulationAnalytics


class ContextAggregator:
    """Builds :class:`DecisionContext` bundles from a source population."""

    def build_context(
        self,
        population: SourcePopulation,
        case_id: str,
        *,
        population_analytics: PopulationAnalytics | None = None,
        schema_version: str = "v2.p6.1",
    ) -> DecisionContext:
        case = population.case(case_id)
        if case is None:
            raise KeyError(f"case not found in population: {case_id!r}")
        patient = population.patient(case.patient_id)
        if patient is None:
            raise KeyError(f"patient not found for case {case_id!r}: {case.patient_id!r}")

        reviews = population.reviews_for_case(case_id)
        findings = population.findings_for_case(case_id)

        interpretations = tuple(
            i
            for f in findings
            for i in population.interpretations_for_finding(f.finding_id)
        )
        evidence = tuple(sorted(
            (e for e in population.evidence if e.case_id == case_id),
            key=lambda e: e.evidence_id,
        ))
        categories = {f.category for f in findings}
        knowledge = tuple(sorted(
            (k for k in population.knowledge if k.finding_category in categories),
            key=lambda k: k.knowledge_id,
        ))

        n_findings = len(findings)
        findings_with_interp = sum(
            1 for f in findings if population.interpretations_for_finding(f.finding_id)
        )
        findings_with_evidence = sum(1 for f in findings if f.evidence_ids)
        mean_review_completeness = (
            quantize(sum(r.completeness for r in reviews) / len(reviews)) if reviews else 0.0
        )
        completeness = {
            "mean_review_completeness": mean_review_completeness,
            "finalized_review_rate": quantize(
                sum(1 for r in reviews if r.is_finalized) / len(reviews)
            )
            if reviews
            else 0.0,
            "interpretation_coverage": quantize(findings_with_interp / n_findings)
            if n_findings
            else 0.0,
            "evidence_coverage": quantize(findings_with_evidence / n_findings)
            if n_findings
            else 0.0,
        }
        counts = {
            "reviews": len(reviews),
            "findings": n_findings,
            "interpretations": len(interpretations),
            "evidence": len(evidence),
            "knowledge": len(knowledge),
        }

        population_context = self._population_context(population_analytics, categories)

        context_id = DecisionContext.mint_id(case_id)
        return DecisionContext(
            id=context_id,
            schema_version=schema_version,
            patient_ref=patient.ref(),
            case_ref=case.ref(),
            review_refs=tuple(r.ref() for r in reviews),
            finding_refs=tuple(f.ref() for f in findings),
            interpretation_refs=tuple(i.ref() for i in interpretations),
            knowledge_refs=tuple(k.ref() for k in knowledge),
            evidence_refs=tuple(e.ref() for e in evidence),
            completeness=completeness,
            counts=counts,
            population_context=population_context,
        )

    def _population_context(
        self, analytics: PopulationAnalytics | None, categories
    ) -> dict:
        if analytics is None:
            return {}
        block = analytics.block(ArtifactKind.FINDING)
        if block is None:
            return {"analytics_ref": analytics.ref().id}
        freq = dict(block.frequency)
        return {
            "analytics_ref": analytics.ref().id,
            "population_finding_count": block.count,
            "category_frequency": {
                c.value: freq.get(c.value, 0.0) for c in sorted(categories, key=lambda c: c.value)
            },
        }
