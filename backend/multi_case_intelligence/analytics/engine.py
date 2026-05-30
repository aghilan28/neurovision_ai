"""Deterministic population analytics engine.

Builds a :class:`PopulationAnalytics` artifact containing one
:class:`StatisticBlock` per subject kind. The engine reads the population and
produces only derived statistics and references; it never alters source records.
"""

from __future__ import annotations

from typing import Sequence

from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.base import ArtifactKind, ArtifactRef
from backend.multi_case_intelligence.schemas.intelligence import (
    Cohort,
    PopulationAnalytics,
    StatisticBlock,
)
from backend.multi_case_intelligence.schemas.source import (
    Evidence,
    Finding,
    Review,
)
from backend.multi_case_intelligence.statistics import functions as fn


class AnalyticsEngine:
    """Computes statistic blocks over a source population (read-only)."""

    # -- public API -------------------------------------------------------- #
    def analyze_population(
        self, population: SourcePopulation, *, scope: str = "population", schema_version: str = "v2.p5.1"
    ) -> PopulationAnalytics:
        """Statistics for the whole population across all five subject kinds."""
        blocks = (
            self._case_block(population),
            self._review_block(population),
            self._finding_block(population, population.findings),
            self._evidence_block(population, population.evidence),
            self._knowledge_block(population),
        )
        return self._assemble(scope, blocks, cohort_ref=None, schema_version=schema_version)

    def analyze_cohort(
        self, population: SourcePopulation, cohort: Cohort, *, schema_version: str = "v2.p5.1"
    ) -> PopulationAnalytics:
        """Statistics for a single cohort, restricted to its members."""
        members = set(cohort.members)
        kind = cohort.member_kind
        if kind == ArtifactKind.FINDING:
            block = self._finding_block(
                population, tuple(f for f in population.findings if f.finding_id in members)
            )
        elif kind == ArtifactKind.EVIDENCE:
            block = self._evidence_block(
                population, tuple(e for e in population.evidence if e.evidence_id in members)
            )
        elif kind == ArtifactKind.REVIEW:
            block = self._review_block(
                population, tuple(r for r in population.reviews if r.review_id in members)
            )
        elif kind == ArtifactKind.CASE:
            block = self._case_block(
                population, tuple(c for c in population.cases if c.case_id in members)
            )
        elif kind == ArtifactKind.KNOWLEDGE:
            block = self._knowledge_block(
                population, tuple(k for k in population.knowledge if k.knowledge_id in members)
            )
        else:
            raise ValueError(f"unsupported cohort member kind for analytics: {kind}")
        return self._assemble(
            f"cohort:{cohort.id}", (block,), cohort_ref=cohort.ref(), schema_version=schema_version
        )

    # -- assembly ---------------------------------------------------------- #
    def _assemble(
        self,
        scope: str,
        blocks: Sequence[StatisticBlock],
        *,
        cohort_ref: ArtifactRef | None,
        schema_version: str,
    ) -> PopulationAnalytics:
        analytics_id = PopulationAnalytics.mint_id(scope)
        return PopulationAnalytics(
            id=analytics_id,
            schema_version=schema_version,
            scope=scope,
            cohort_ref=cohort_ref,
            blocks=tuple(blocks),
        )

    # -- per-kind blocks --------------------------------------------------- #
    def _case_block(self, population: SourcePopulation, cases=None) -> StatisticBlock:
        cases = population.cases if cases is None else cases
        by_status = fn.distribution(cases, "status", lambda c: c.status)
        by_site = fn.distribution(cases, "site", lambda c: c.site)
        cov_review, n_rev, _ = fn.coverage(
            cases, lambda c: bool(population.reviews_for_case(c.case_id))
        )
        cov_finding, n_find, _ = fn.coverage(
            cases, lambda c: bool(population.findings_for_case(c.case_id))
        )
        return StatisticBlock(
            subject_kind=ArtifactKind.CASE,
            count=fn.count(cases),
            distributions=(by_status, by_site),
            coverage={"has_review": cov_review, "has_finding": cov_finding},
            variability={
                "status_entropy": fn.normalized_entropy(by_status),
                "site_entropy": fn.normalized_entropy(by_site),
                "distinct_sites": float(fn.distinct_count(by_site)),
            },
            frequency=dict(fn.frequency(by_status)),
            confidence={},
        )

    def _review_block(self, population: SourcePopulation, reviews: Sequence[Review] = None) -> StatisticBlock:
        reviews = population.reviews if reviews is None else reviews
        by_status = fn.distribution(reviews, "status", lambda r: r.status.value)
        by_role = fn.distribution(reviews, "reviewer_role", lambda r: r.reviewer_role)
        cov_final, _, _ = fn.coverage(reviews, lambda r: r.is_finalized)
        cov_complete, _, _ = fn.coverage(reviews, lambda r: r.completeness >= 1.0)
        completeness_vals = [r.completeness for r in reviews]
        return StatisticBlock(
            subject_kind=ArtifactKind.REVIEW,
            count=fn.count(reviews),
            distributions=(by_status, by_role),
            coverage={"finalized": cov_final, "fully_complete": cov_complete},
            variability={"status_entropy": fn.normalized_entropy(by_status)},
            frequency=dict(fn.frequency(by_status)),
            confidence=dict(fn.confidence_aggregates(completeness_vals)),
        )

    def _finding_block(self, population: SourcePopulation, findings: Sequence[Finding]) -> StatisticBlock:
        by_category = fn.distribution(findings, "category", lambda f: f.category.value)
        cov_evidence, _, _ = fn.coverage(findings, lambda f: len(f.evidence_ids) > 0)
        cov_interp, _, _ = fn.coverage(
            findings, lambda f: bool(population.interpretations_for_finding(f.finding_id))
        )
        cov_abstain, _, _ = fn.coverage(
            findings, lambda f: f.signal is not None and f.signal.abstained
        )
        conf_vals = [f.signal.confidence for f in findings if f.signal is not None]
        return StatisticBlock(
            subject_kind=ArtifactKind.FINDING,
            count=fn.count(findings),
            distributions=(by_category,),
            coverage={
                "has_evidence": cov_evidence,
                "has_interpretation": cov_interp,
                "abstained": cov_abstain,
            },
            variability={
                "category_entropy": fn.normalized_entropy(by_category),
                "distinct_categories": float(fn.distinct_count(by_category)),
            },
            frequency=dict(fn.frequency(by_category)),
            confidence=dict(fn.confidence_aggregates(conf_vals)),
        )

    def _evidence_block(self, population: SourcePopulation, evidence: Sequence[Evidence]) -> StatisticBlock:
        by_modality = fn.distribution(evidence, "modality", lambda e: e.modality)
        cov_linked, _, _ = fn.coverage(evidence, lambda e: e.finding_id is not None)
        conf_vals = [e.signal.confidence for e in evidence if e.signal is not None]
        return StatisticBlock(
            subject_kind=ArtifactKind.EVIDENCE,
            count=fn.count(evidence),
            distributions=(by_modality,),
            coverage={"linked_to_finding": cov_linked},
            variability={"modality_entropy": fn.normalized_entropy(by_modality)},
            frequency=dict(fn.frequency(by_modality)),
            confidence=dict(fn.confidence_aggregates(conf_vals)),
        )

    def _knowledge_block(self, population: SourcePopulation, knowledge=None) -> StatisticBlock:
        knowledge = population.knowledge if knowledge is None else knowledge
        by_category = fn.distribution(
            knowledge,
            "finding_category",
            lambda k: "none" if k.finding_category is None else k.finding_category.value,
        )
        cov_refs, _, _ = fn.coverage(knowledge, lambda k: len(k.references) > 0)
        return StatisticBlock(
            subject_kind=ArtifactKind.KNOWLEDGE,
            count=fn.count(knowledge),
            distributions=(by_category,),
            coverage={"has_references": cov_refs},
            variability={"category_entropy": fn.normalized_entropy(by_category)},
            frequency=dict(fn.frequency(by_category)),
            confidence={},
        )
