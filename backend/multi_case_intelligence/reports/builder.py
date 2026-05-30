"""Deterministic intelligence report construction.

Each builder produces an :class:`IntelligenceReport` whose ``sections`` are
plain, serializable summaries and whose ``referenced`` field pins the exact
artifacts the report was built from (so the report is itself traceable).
"""

from __future__ import annotations

from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.schemas.intelligence import (
    Cohort,
    IntelligenceReport,
    PopulationAnalytics,
    QualityReport,
    Trend,
)
from backend.multi_case_intelligence.validation.validators import ValidationReport


class ReportBuilder:
    """Builds versioned :class:`IntelligenceReport` artifacts."""

    def cohort_report(self, cohort: Cohort) -> IntelligenceReport:
        sections = {
            "member_kind": cohort.member_kind.value,
            "size": cohort.size,
            "criteria": {
                "combinator": cohort.criteria.combinator.value,
                "description": cohort.criteria.description,
                "clauses": [
                    {"field": c.field, "op": c.op, "value": c.value}
                    for c in cohort.criteria.clauses
                ],
            },
            "members": list(cohort.members),
        }
        return self._build("cohort", f"Cohort {cohort.id}", sections, (cohort.ref(),))

    def analytics_report(self, analytics: PopulationAnalytics) -> IntelligenceReport:
        sections = {
            "scope": analytics.scope,
            "blocks": [
                {
                    "subject_kind": b.subject_kind.value,
                    "count": b.count,
                    "distributions": {
                        d.field: {cat: n for cat, n in d.counts} for d in b.distributions
                    },
                    "coverage": dict(b.coverage),
                    "variability": dict(b.variability),
                    "frequency": dict(b.frequency),
                    "confidence": dict(b.confidence),
                }
                for b in analytics.blocks
            ],
        }
        refs = (analytics.ref(),) + ((analytics.cohort_ref,) if analytics.cohort_ref else ())
        return self._build("analytics", f"Analytics {analytics.scope}", sections, refs)

    def trend_report(self, trend: Trend) -> IntelligenceReport:
        sections = {
            "scope": trend.scope,
            "series": [
                {
                    "metric": s.metric,
                    "subject_kind": s.subject_kind.value,
                    "direction": s.direction.value,
                    "delta": s.delta,
                    "points": [
                        {"bucket": p.bucket, "value": p.value, "count": p.count}
                        for p in s.points
                    ],
                }
                for s in trend.series
            ],
        }
        return self._build("trend", f"Trends {trend.scope}", sections, (trend.ref(),))

    def quality_report(self, quality: QualityReport) -> IntelligenceReport:
        sections = {
            "scope": quality.scope,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "numerator": m.numerator,
                    "denominator": m.denominator,
                    "description": m.description,
                }
                for m in quality.metrics
            ],
        }
        return self._build("quality", f"Quality {quality.scope}", sections, (quality.ref(),))

    def population_report(
        self,
        analytics: PopulationAnalytics,
        quality: QualityReport,
        trend: Trend | None = None,
    ) -> IntelligenceReport:
        sections = {
            "scope": analytics.scope,
            "population_counts": {b.subject_kind.value: b.count for b in analytics.blocks},
            "quality": {m.name: m.value for m in quality.metrics},
            "trend_directions": (
                {s.metric: s.direction.value for s in trend.series} if trend else {}
            ),
        }
        refs = [analytics.ref(), quality.ref()]
        if trend is not None:
            refs.append(trend.ref())
        return self._build("population", f"Population {analytics.scope}", sections, tuple(refs))

    def validation_report(
        self, report: ValidationReport, referenced: tuple[ArtifactRef, ...] = ()
    ) -> IntelligenceReport:
        sections = {
            "scope": report.scope,
            "passed": report.passed,
            "results": [
                {"name": r.name, "passed": r.passed, "detail": r.detail}
                for r in report.results
            ],
        }
        return self._build("validation", f"Validation {report.scope}", sections, referenced)

    # -- helper ------------------------------------------------------------ #
    def _build(
        self, report_type: str, title: str, sections: dict, referenced: tuple[ArtifactRef, ...]
    ) -> IntelligenceReport:
        report_id = IntelligenceReport.mint_id(report_type, title)
        return IntelligenceReport(
            id=report_id,
            report_type=report_type,
            title=title,
            sections=sections,
            referenced=referenced,
        )
