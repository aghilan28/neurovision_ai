"""Analytics builder (V3-P5) — assembles AnalyticsRecords from upstream artifacts.

Combines the six analytics engines (metrics, health, performance, quality, trend,
risk) into derived :class:`AnalyticsRecord` artifacts. Everything is read from the
already-governed upstream artifacts via the :class:`AnalyticsSourceView` — no
analytics-only truth. The builder mints one record per requested category, plus a
composite ``operational`` record that summarizes the headline signal of each
dimension.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..identity import mint_analytics
from ..models.categories import AnalyticsCategory
from ..models.domain import AnalyticsMetric, AnalyticsRecord
from ..models.source import AnalyticsSourceView
from ..metrics import MetricsEngine
from ..health import HealthEngine
from ..performance import PerformanceEngine
from ..quality import QualityEngine
from ..trends import TrendEngine
from ..risk import RiskEngine

# category -> (engine instance, headline metric name for the operational summary)
_HEADLINE = {
    AnalyticsCategory.METRICS: "event_total",
    AnalyticsCategory.HEALTH: "operational_health",
    AnalyticsCategory.PERFORMANCE: "operational_efficiency",
    AnalyticsCategory.QUALITY: "workflow_quality",
    AnalyticsCategory.TREND: "operational_trend",
    AnalyticsCategory.RISK: "operational_risk",
}


class AnalyticsBuilder:
    """Builds :class:`AnalyticsRecord` artifacts from upstream artifacts (read-only)."""

    def __init__(self) -> None:
        self._engines = {
            AnalyticsCategory.METRICS: MetricsEngine(),
            AnalyticsCategory.HEALTH: HealthEngine(),
            AnalyticsCategory.PERFORMANCE: PerformanceEngine(),
            AnalyticsCategory.QUALITY: QualityEngine(),
            AnalyticsCategory.TREND: TrendEngine(),
            AnalyticsCategory.RISK: RiskEngine(),
        }

    # --- single category ------------------------------------------------------
    def build_category(self, category: str, view: AnalyticsSourceView, *,
                       subject_kind: str = "operational", subject_id: str = "all",
                       scope: Optional[str] = None) -> AnalyticsRecord:
        if category not in self._engines:
            raise KeyError(f"no analytics engine for category {category!r}")
        metrics = tuple(self._engines[category].compute(view))
        scope = scope or f"{category}:{subject_kind}:{subject_id}"
        ident = mint_analytics(category, scope)
        summary = self._summarize(category, metrics)
        return AnalyticsRecord(
            analytics_id=ident.id, category=category, scope=scope, subject_kind=subject_kind,
            subject_id=subject_id, metrics=metrics, sources=view.source_refs(), summary=summary)

    # --- composite operational summary ---------------------------------------
    def build_operational(self, view: AnalyticsSourceView, *, subject_kind: str = "operational",
                          subject_id: str = "all") -> AnalyticsRecord:
        """One record holding the headline metric of each dimension (derived view)."""
        headline: list[AnalyticsMetric] = []
        for category, engine in self._engines.items():
            produced = {m.name: m for m in engine.compute(view)}
            name = _HEADLINE[category]
            if name in produced:
                headline.append(produced[name])
        scope = f"{AnalyticsCategory.OPERATIONAL}:{subject_kind}:{subject_id}"
        ident = mint_analytics(AnalyticsCategory.OPERATIONAL, scope)
        summary = (f"operational summary over {len(view.events())} events, "
                   f"{len(view.workflows())} workflows, {len(view.graph_node_ids())} graph nodes")
        return AnalyticsRecord(
            analytics_id=ident.id, category=AnalyticsCategory.OPERATIONAL, scope=scope,
            subject_kind=subject_kind, subject_id=subject_id, metrics=tuple(headline),
            sources=view.source_refs(), summary=summary)

    # --- all categories -------------------------------------------------------
    def build_all(self, view: AnalyticsSourceView, *, subject_kind: str = "operational",
                  subject_id: str = "all") -> list[AnalyticsRecord]:
        records = [self.build_category(c, view, subject_kind=subject_kind, subject_id=subject_id)
                   for c in self._engines]
        records.append(self.build_operational(view, subject_kind=subject_kind, subject_id=subject_id))
        return records

    # --- internals ------------------------------------------------------------
    @staticmethod
    def _summarize(category: str, metrics: Sequence[AnalyticsMetric]) -> str:
        observed = [m for m in metrics if m.observed]
        return (f"{category}: {len(observed)}/{len(metrics)} metrics observed")
