"""Deterministic population analytics engine (V2-P5).

Builds a :class:`PopulationAnalytics` artifact containing one
:class:`StatisticBlock` per subject kind (case/review/finding/interpretation/
knowledge). The engine reads the population and produces only derived statistics;
it never alters source records.
"""

from __future__ import annotations

from typing import Sequence

from backend.clinical_findings.models.domain import FindingStatus
from backend.clinical_review.models.domain import ReviewStatus

from ..identity import mint_analytics
from ..models.domain import Cohort, CohortKind, PopulationAnalytics, StatisticBlock
from ..population import PopulationView, finding_confidence
from ..statistics import statistics as st

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}


class AnalyticsEngine:
    """Computes statistic blocks over a population (read-only)."""

    def analyze_population(self, population: PopulationView, *, scope: str = "population") -> PopulationAnalytics:
        blocks = (
            self._case_block(population, population.cases),
            self._review_block(population, population.reviews),
            self._finding_block(population, population.findings),
            self._interpretation_block(population, population.interpretations),
            self._concept_block(population, population.concepts),
        )
        ident = mint_analytics(scope)
        return PopulationAnalytics(analytics_id=ident.id, scope=scope, blocks=blocks)

    def analyze_cohort(self, population: PopulationView, cohort: Cohort) -> PopulationAnalytics:
        members = set(cohort.members)
        kind = cohort.definition.member_kind
        scope = f"cohort:{cohort.cohort_id}"
        if kind is CohortKind.FINDING:
            block = self._finding_block(population, [f for f in population.findings if f.finding_id in members])
        elif kind is CohortKind.REVIEW:
            block = self._review_block(population, [r for r in population.reviews if r.review_id in members])
        elif kind is CohortKind.CASE:
            block = self._case_block(population, [c for c in population.cases if c.case_id in members])
        elif kind is CohortKind.INTERPRETATION:
            block = self._interpretation_block(
                population, [i for i in population.interpretations if i.interpretation_id in members])
        elif kind is CohortKind.CONCEPT:
            block = self._concept_block(population, [c for c in population.concepts if c.concept_id in members])
        else:  # pragma: no cover - guarded by CohortKind
            raise ValueError(f"unsupported cohort kind {kind!r}")
        ident = mint_analytics(scope)
        return PopulationAnalytics(analytics_id=ident.id, scope=scope, blocks=(block,), cohort_id=cohort.cohort_id)

    # --- per-kind blocks ------------------------------------------------------
    def _case_block(self, pop: PopulationView, cases: Sequence) -> StatisticBlock:
        by_status = st.distribution(cases, lambda c: c.state.status.value)
        by_patient = st.distribution(cases, lambda c: c.patient_id)
        return StatisticBlock(
            subject_kind="case", count=st.count(cases),
            distributions={"status": by_status, "patient": by_patient},
            coverage={"has_review": st.coverage(cases, lambda c: bool(pop.reviews_for_case(c.case_id))),
                      "has_finding": st.coverage(cases, lambda c: bool(pop.findings_for_case(c.case_id)))},
            variability={"status_entropy": st.normalized_entropy(by_status),
                         "distinct_patients": float(st.distinct_count(by_patient))},
            frequency=st.frequency(by_status), confidence={})

    def _review_block(self, pop: PopulationView, reviews: Sequence) -> StatisticBlock:
        by_status = st.distribution(reviews, lambda r: r.status.value)
        return StatisticBlock(
            subject_kind="review", count=st.count(reviews),
            distributions={"status": by_status},
            coverage={"finalized": st.coverage(reviews, lambda r: r.status in _FINALIZED_REVIEW),
                      "has_reviewer": st.coverage(reviews, lambda r: bool(r.reviewer))},
            variability={"status_entropy": st.normalized_entropy(by_status)},
            frequency=st.frequency(by_status), confidence={})

    def _finding_block(self, pop: PopulationView, findings: Sequence) -> StatisticBlock:
        by_category = st.distribution(findings, lambda f: f.record.category)
        by_status = st.distribution(findings, lambda f: f.status.value)
        confs = [finding_confidence(f) for f in findings]
        return StatisticBlock(
            subject_kind="finding", count=st.count(findings),
            distributions={"category": by_category, "status": by_status},
            coverage={
                "has_interpretation": st.coverage(findings, lambda f: len(f.interpretation_ids) > 0),
                "confirmed": st.coverage(findings, lambda f: f.status == FindingStatus.CONFIRMED),
                "known_category": st.coverage(findings, lambda f: pop.category_is_known(f.record.category)),
                "has_recorded_confidence": st.coverage(findings, lambda f: finding_confidence(f) is not None),
            },
            variability={"category_entropy": st.normalized_entropy(by_category),
                         "distinct_categories": float(st.distinct_count(by_category))},
            frequency=st.frequency(by_category),
            confidence=st.numeric_aggregates([c for c in confs if c is not None]))

    def _interpretation_block(self, pop: PopulationView, interps: Sequence) -> StatisticBlock:
        by_level = st.distribution(interps, lambda i: str(i.confidence_level))
        return StatisticBlock(
            subject_kind="interpretation", count=st.count(interps),
            distributions={"confidence_level": by_level},
            coverage={"has_concept_ref": st.coverage(interps, lambda i: len(i.concept_refs) > 0),
                      "evidence_grounded": st.coverage(interps, lambda i: len(i.supporting_evidence) > 0)},
            variability={"confidence_level_entropy": st.normalized_entropy(by_level)},
            frequency=st.frequency(by_level), confidence={})

    def _concept_block(self, pop: PopulationView, concepts: Sequence) -> StatisticBlock:
        by_status = st.distribution(concepts, lambda c: c.status)
        return StatisticBlock(
            subject_kind="concept", count=st.count(concepts),
            distributions={"status": by_status},
            coverage={"has_evidence_link": st.coverage(concepts, lambda c: len(c.evidence_links) > 0),
                      "has_related_terms": st.coverage(concepts, lambda c: len(c.related_terms) > 0)},
            variability={"status_entropy": st.normalized_entropy(by_status),
                         "n_terms": float(len(pop.terms))},
            frequency=st.frequency(by_status), confidence={})
