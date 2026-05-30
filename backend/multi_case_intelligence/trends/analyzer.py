"""Deterministic trend analysis.

Trends are series over the sorted, distinct case ``ordinal`` values (a logical
ordering supplied by the upstream case layer). For each bucket the analyzer
computes finding/evidence/review/knowledge/cohort metrics. Direction is derived
from the first and last observed values with a fixed epsilon, so it is fully
reproducible.
"""

from __future__ import annotations

from typing import Callable, Sequence

from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.determinism import quantize
from backend.multi_case_intelligence.schemas.intelligence import (
    Trend,
    TrendDirection,
    TrendPoint,
    TrendSeries,
)
from backend.multi_case_intelligence.schemas.source import ClinicalCase

# Below this absolute first->last delta a series is reported as FLAT.
TREND_EPSILON = 1e-9


class TrendAnalyzer:
    """Computes :class:`Trend` artifacts over the ordinal dimension (read-only)."""

    def analyze(
        self, population: SourcePopulation, *, scope: str = "population", schema_version: str = "v2.p5.1"
    ) -> Trend:
        buckets = sorted({c.ordinal for c in population.cases})
        cases_by_bucket: dict[int, list[ClinicalCase]] = {b: [] for b in buckets}
        for c in population.cases:
            cases_by_bucket[c.ordinal].append(c)

        knowledge_categories = {
            k.finding_category for k in population.knowledge if k.finding_category is not None
        }

        def finding_count(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            findings = [f for c in cases for f in population.findings_for_case(c.case_id)]
            return float(len(findings)), len(findings)

        def evidence_count(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            n = 0
            for c in cases:
                for f in population.findings_for_case(c.case_id):
                    n += len(population.evidence_for_finding(f.finding_id))
            return float(n), n

        def review_finalized_rate(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            reviews = [r for c in cases for r in population.reviews_for_case(c.case_id)]
            if not reviews:
                return 0.0, 0
            final = sum(1 for r in reviews if r.is_finalized)
            return quantize(final / len(reviews)), len(reviews)

        def finding_mean_confidence(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            confs = [
                f.signal.confidence
                for c in cases
                for f in population.findings_for_case(c.case_id)
                if f.signal is not None
            ]
            if not confs:
                return 0.0, 0
            return quantize(sum(confs) / len(confs)), len(confs)

        def knowledge_linked_rate(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            findings = [f for c in cases for f in population.findings_for_case(c.case_id)]
            if not findings:
                return 0.0, 0
            linked = sum(1 for f in findings if f.category in knowledge_categories)
            return quantize(linked / len(findings)), len(findings)

        def cohort_size(cases: Sequence[ClinicalCase]) -> tuple[float, int]:
            return float(len(cases)), len(cases)

        series = (
            self._series("finding_count", ArtifactKind.FINDING, buckets, cases_by_bucket, finding_count),
            self._series("evidence_count", ArtifactKind.EVIDENCE, buckets, cases_by_bucket, evidence_count),
            self._series("review_finalized_rate", ArtifactKind.REVIEW, buckets, cases_by_bucket, review_finalized_rate),
            self._series("finding_mean_confidence", ArtifactKind.FINDING, buckets, cases_by_bucket, finding_mean_confidence),
            self._series("knowledge_linked_rate", ArtifactKind.KNOWLEDGE, buckets, cases_by_bucket, knowledge_linked_rate),
            self._series("cohort_size", ArtifactKind.CASE, buckets, cases_by_bucket, cohort_size),
        )
        trend_id = Trend.mint_id(scope)
        return Trend(id=trend_id, schema_version=schema_version, scope=scope, series=series)

    def _series(
        self,
        metric: str,
        subject_kind: ArtifactKind,
        buckets: Sequence[int],
        cases_by_bucket: dict[int, list[ClinicalCase]],
        value_fn: Callable[[Sequence[ClinicalCase]], tuple[float, int]],
    ) -> TrendSeries:
        points: list[TrendPoint] = []
        for b in buckets:
            value, n = value_fn(cases_by_bucket[b])
            points.append(TrendPoint(bucket=str(b), value=quantize(value), count=n))
        direction, delta = self._direction(points)
        return TrendSeries(
            metric=metric,
            subject_kind=subject_kind,
            points=tuple(points),
            direction=direction,
            delta=delta,
        )

    @staticmethod
    def _direction(points: Sequence[TrendPoint]) -> tuple[TrendDirection, float]:
        if len(points) < 2:
            return TrendDirection.INSUFFICIENT, 0.0
        delta = quantize(points[-1].value - points[0].value)
        if delta > TREND_EPSILON:
            return TrendDirection.INCREASING, delta
        if delta < -TREND_EPSILON:
            return TrendDirection.DECREASING, delta
        return TrendDirection.FLAT, delta
