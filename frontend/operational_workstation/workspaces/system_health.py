"""System Health workspace — the unified operational status landing area.

Surfaces the platform-wide health/risk headline (from the analytics ``operational``
+ ``health`` + ``risk`` dimensions) and a subsystem status board. Presentation only:
every value is read from a registered analytics artifact or audit log.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import analytics_metrics, risk_scores


def _metric(block: dict, name: str):
    for m in block.get("artifact", {}).get("metrics", []):
        if m.get("name") == name:
            return m
    return None


def system_health_pages(state) -> list:
    blocks = state.analytics_blocks
    health = blocks.get("health", {})
    risk = blocks.get("risk", {})
    meta = state.meta

    sys_health = _metric(health, "system_health_score")
    op_health = _metric(health, "operational_health")
    op_risk = _metric(risk, "operational_risk")

    # subsystem status board (presence + audit verification)
    subsystems = [
        ("Events (V3-P1)", state.events.get("audit", {}).get("verified", False)),
        ("Temporal (V3-P2)", state.timelines.get("audit", {}).get("verified", False)),
        ("Workflows (V3-P3)", state.workflows.get("audit", {}).get("verified", False)),
        ("Graph (V3-P4)", state.graph.get("audit", {}).get("verified", False)),
        ("Analytics (V3-P5)", state.analytics.get("audit", {}).get("verified", False)),
        ("Recommendations (V3-P6)", state.recommendations.get("audit", {}).get("verified", False)),
    ]

    counts_rows = [
        ["events", meta.get("n_events")], ["workflows", meta.get("n_workflows")],
        ["graph nodes", meta.get("n_nodes")], ["graph edges", meta.get("n_edges")],
        ["analytics", meta.get("n_analytics")],
        ["recommendations", meta.get("n_recommendations")],
        ["cases", meta.get("n_cases")],
    ]

    sections = [
        kv_panel("System Health", {
            "system_health_score": round(sys_health["value"], 4) if sys_health else "n/a",
            "operational_health": round(op_health["value"], 4) if op_health else "n/a",
            "operational_risk": round(op_risk["value"], 4) if op_risk else "n/a",
            "chain_verified": state.representative_chain.get("verified"),
        }),
        badges("Subsystem Status (audit verified)", subsystems),
        table("Operational Counts", ["artifact", "count"], counts_rows),
    ]
    viz = [analytics_metrics(health.get("artifact", {}), title="Health Scores"),
           risk_scores(risk.get("artifact", {}))]
    return [Page("system-health", "System Health", sections, viz)]
