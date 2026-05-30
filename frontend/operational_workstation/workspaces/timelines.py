"""Timeline workspace — timelines, histories, evolution, temporal analytics."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import timeline_evolution, audit_timeline


def timeline_pages(state) -> list:
    block = state.timelines
    registry = block.get("registry", {})
    op_tl = block.get("operational_timeline", {})
    tl = block.get("timeline", {})
    hist = block.get("history", {})
    evo = block.get("evolution", {})
    analytics = block.get("analytics", {})
    audit = block.get("audit", {})

    op_artifact = op_tl.get("artifact", {})
    analytics_artifact = analytics.get("artifact", {})
    duration_rows = [[m.get("name"), m.get("steps"), m.get("observed"), m.get("detail", "")[:40]]
                     for m in analytics_artifact.get("metrics", [])]

    sections = [
        kv_panel("Temporal Registry", {
            "temporal_registry_version": registry.get("temporal_registry_version"),
            "n_artifacts": registry.get("n_records", registry.get("n_artifacts")),
            "audit_verified": audit.get("verified"),
        }),
        kv_panel("Operational Timeline", {
            "n_points": op_artifact.get("n_points", len(op_artifact.get("points", []))),
            "scope": op_artifact.get("scope"),
            "lineage_verified": op_tl.get("lineage_verified"),
        }),
        badges("Timeline / History / Evolution / Analytics validation", [
            ("timeline", tl.get("validation", {}).get("ok", False)),
            ("history", hist.get("validation", {}).get("ok", False)),
            ("evolution", evo.get("validation", {}).get("ok", False)),
            ("temporal_analytics", analytics.get("validation", {}).get("ok", False)),
        ]),
        table("Temporal Analytics (duration metrics, logical steps)",
              ["metric", "steps", "observed", "detail"], duration_rows),
    ]
    viz = [timeline_evolution(evo.get("artifact", {})),
           audit_timeline(audit.get("events", []), title="Temporal Audit Timeline")]
    return [Page("timelines", "Timelines", sections, viz)]
