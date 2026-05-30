"""Context engine (V3-P6).

Aggregates a deterministic :class:`RecommendationContext` bundle from operational
intelligence: analytics context (per-dimension headline metrics), workflow context,
graph context, temporal context, risk context, and health context. The bundle is a
derived view — it adds no new truth; it selects/summarizes existing analytics,
workflow and graph signals so the downstream engines reason over one explainable,
reproducible context.
"""

from __future__ import annotations

from backend.operational_analytics import AnalyticsCategory as AC  # intra-backend reuse

from ..identity import mint_recommendation
from ..models.domain import RecommendationContext
from ..models.source import RecommendationSourceView
from ..version import RECOMMENDATION_CONTEXT_ENGINE_VERSION
from ._common import rnd


class ContextEngine:
    """Builds a :class:`RecommendationContext` from operational intelligence (read-only)."""

    engine_version = RECOMMENDATION_CONTEXT_ENGINE_VERSION

    def build(self, view: RecommendationSourceView, *, scope: str = "operational:all") -> RecommendationContext:
        # analytics context: the headline metric of each analytics dimension
        analytics_context: dict = {}
        for category in (AC.METRICS, AC.HEALTH, AC.PERFORMANCE, AC.QUALITY, AC.TREND, AC.RISK):
            rec = view.first_of_category(category)
            if rec is None:
                continue
            analytics_context[category] = {
                "analytics_id": rec.analytics_id,
                "metrics": {m.name: rnd(m.value) for m in rec.metrics if m.observed},
            }

        # workflow context: counts + bottleneck signal
        workflows = view.workflows()
        n_bottlenecked = sum(1 for w in workflows if w.metadata.bottlenecks)
        workflow_context = {
            "n_workflows": len(workflows),
            "workflow_ids": view.workflow_ids(),
            "n_bottlenecked": n_bottlenecked,
            "bottlenecks": sorted({b for w in workflows for b in w.metadata.bottlenecks}),
        }

        # graph context: size
        graph_context = {"n_nodes": len(view.graph_node_ids()),
                         "has_graph": view.has_graph()}

        # temporal context: headline trend metrics
        trend_rec = view.first_of_category(AC.TREND)
        temporal_context = ({"trend_metrics": {m.name: rnd(m.value)
                                               for m in trend_rec.metrics if m.observed}}
                            if trend_rec is not None else {})

        # risk context: all observed risk scores
        risk_rec = view.first_of_category(AC.RISK)
        risk_context = ({"risk_scores": {m.name: rnd(m.value)
                                         for m in risk_rec.metrics if m.observed}}
                        if risk_rec is not None else {})

        # health context: all observed health scores
        health_rec = view.first_of_category(AC.HEALTH)
        health_context = ({"health_scores": {m.name: rnd(m.value)
                                             for m in health_rec.metrics if m.observed}}
                          if health_rec is not None else {})

        ident = mint_recommendation("context", scope)
        return RecommendationContext(
            context_id="context+" + ident.id.split("+", 1)[1], scope=scope,
            analytics_context=analytics_context, workflow_context=workflow_context,
            graph_context=graph_context, temporal_context=temporal_context,
            risk_context=risk_context, health_context=health_context)
