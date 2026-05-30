"""Global navigation — assemble the ten primary nav areas, preserving context.

Each area owns the pages built by a workspace module and carries a deterministic
``context`` block (the current event/timeline/workflow/graph/analytics/
recommendation/audit/lineage selection) so navigating between areas preserves
operational context. Navigation is presentation-only: it records selections, it
never mutates source artifacts.
"""

from __future__ import annotations

from ..schemas import NavArea
from ..workspaces import (
    event_pages, timeline_pages, workflow_pages, graph_pages, analytics_pages,
    recommendation_pages, audit_pages, lineage_pages, report_pages, system_health_pages,
)

# The ten mandated primary areas, in display order, with their page builders.
PRIMARY_AREAS = [
    ("system-health", "System Health", system_health_pages),
    ("events", "Events", event_pages),
    ("timelines", "Timelines", timeline_pages),
    ("workflows", "Workflows", workflow_pages),
    ("graph", "Graph", graph_pages),
    ("analytics", "Analytics", analytics_pages),
    ("recommendations", "Recommendations", recommendation_pages),
    ("audit", "Audit", audit_pages),
    ("lineage", "Lineage", lineage_pages),
    ("reports", "Reports", report_pages),
]


def build_areas(state) -> list:
    """Build every primary nav area from the workstation state (context preserved)."""
    context = state.context_snapshot()
    areas = []
    for area_id, title, builder in PRIMARY_AREAS:
        pages = builder(state)
        areas.append(NavArea(id=area_id, title=title, pages=pages, context=dict(context)))
    return areas


def area_ids() -> list:
    return [a[0] for a in PRIMARY_AREAS]
