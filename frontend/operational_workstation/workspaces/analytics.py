"""Analytics workspace — metrics, health, performance, quality, trends, risk."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import analytics_metrics, trend_indices, risk_scores


def _metric_rows(block: dict) -> list:
    artifact = block.get("artifact", {})
    return [[m.get("name"), round(float(m.get("value", 0.0)), 4), m.get("unit"),
             m.get("observed")]
            for m in artifact.get("metrics", [])]


def analytics_pages(state) -> list:
    block = state.analytics
    registry = block.get("registry", {})
    blocks = state.analytics_blocks
    audit = block.get("audit", {})

    health = blocks.get("health", {})
    performance = blocks.get("performance", {})
    quality = blocks.get("quality", {})
    trend = blocks.get("trend", {})
    risk = blocks.get("risk", {})
    metrics = blocks.get("metrics", {})

    sections = [
        kv_panel("Analytics Registry", {
            "n_analytics": block.get("n_analytics"),
            "analytics_registry_version": registry.get("analytics_registry_version"),
            "audit_verified": audit.get("verified"),
        }),
        badges("Analytics Validation (per dimension)",
               [(cat, b.get("validation", {}).get("ok", False))
                for cat, b in sorted(blocks.items())]),
        table("Metrics", ["metric", "value", "unit", "observed"], _metric_rows(metrics)),
        table("Health Scores", ["metric", "value", "unit", "observed"], _metric_rows(health)),
        table("Performance", ["metric", "value", "unit", "observed"],
              _metric_rows(performance)),
        table("Quality", ["metric", "value", "unit", "observed"], _metric_rows(quality)),
        table("Risk Scores", ["metric", "value", "unit", "observed"], _metric_rows(risk)),
    ]
    viz = [analytics_metrics(health.get("artifact", {}), title="Health Scores"),
           trend_indices(trend.get("artifact", {})),
           risk_scores(risk.get("artifact", {}))]
    return [Page("analytics", "Analytics", sections, viz)]
