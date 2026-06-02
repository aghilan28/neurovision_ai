"""Deterministic trend analysis (V2-P5).

Trends are series over a *deterministic ordinal dimension* — never a wall-clock
timestamp (all source ``created_at`` are the deterministic epoch). The natural,
reproducible ordering is the canonical lifecycle-stage order of findings and
reviews, plus a per-patient case-load series. Direction is derived from the first
and last observed values with a fixed epsilon.
"""

from __future__ import annotations

from typing import Sequence

from backend.clinical_findings.models.domain import FindingStatus
from backend.clinical_review.models.domain import ReviewStatus

from ..identity import mint_trend
from ..models.domain import Trend, TrendPoint, TrendSeries
from ..population import PopulationView, finding_confidence

TREND_EPSILON = 1e-9


def _direction(points: Sequence[TrendPoint]) -> tuple[str, float]:
    nonzero = [p for p in points if p.n > 0]
    if len(nonzero) < 2:
        return "insufficient_data", 0.0
    delta = round(nonzero[-1].value - nonzero[0].value, 6)
    if delta > TREND_EPSILON:
        return "increasing", delta
    if delta < -TREND_EPSILON:
        return "decreasing", delta
    return "flat", delta


class TrendAnalyzer:
    """Computes :class:`Trend` artifacts over deterministic ordinal dimensions."""

    def analyze(self, population: PopulationView, *, scope: str = "population") -> Trend:
        series = (
            self._finding_status_progression(population),
            self._finding_confidence_by_status(population),
            self._review_status_progression(population),
            self._cases_per_patient(population),
        )
        ident = mint_trend(scope)
        return Trend(trend_id=ident.id, scope=scope, series=series)

    def _finding_status_progression(self, pop: PopulationView) -> TrendSeries:
        points = []
        for status in FindingStatus:
            n = sum(1 for f in pop.findings if f.status == status)
            points.append(TrendPoint(bucket=status.value, value=float(n), n=n))
        direction, delta = _direction(points)
        return TrendSeries(metric="finding_status_progression", subject_kind="finding",
                           dimension="finding_lifecycle", points=tuple(points),
                           direction=direction, delta=delta)

    def _finding_confidence_by_status(self, pop: PopulationView) -> TrendSeries:
        points = []
        for status in FindingStatus:
            confs = [finding_confidence(f) for f in pop.findings if f.status == status]
            confs = [c for c in confs if c is not None]
            value = round(sum(confs) / len(confs), 6) if confs else 0.0
            points.append(TrendPoint(bucket=status.value, value=value, n=len(confs)))
        direction, delta = _direction(points)
        return TrendSeries(metric="finding_mean_confidence_by_status", subject_kind="finding",
                           dimension="finding_lifecycle", points=tuple(points),
                           direction=direction, delta=delta)

    def _review_status_progression(self, pop: PopulationView) -> TrendSeries:
        points = []
        for status in ReviewStatus:
            n = sum(1 for r in pop.reviews if r.status == status)
            points.append(TrendPoint(bucket=status.value, value=float(n), n=n))
        direction, delta = _direction(points)
        return TrendSeries(metric="review_status_progression", subject_kind="review",
                           dimension="review_lifecycle", points=tuple(points),
                           direction=direction, delta=delta)

    def _cases_per_patient(self, pop: PopulationView) -> TrendSeries:
        points = []
        for pid in pop.patient_ids():
            n = sum(1 for c in pop.cases if c.patient_id == pid)
            points.append(TrendPoint(bucket=pid, value=float(n), n=n))
        direction, delta = _direction(points)
        return TrendSeries(metric="cases_per_patient", subject_kind="case",
                           dimension="patient", points=tuple(points),
                           direction=direction, delta=delta)
