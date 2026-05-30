"""Operational workstation workspaces (V3-P7) — one builder per primary area."""

from __future__ import annotations

from .events import event_pages
from .timelines import timeline_pages
from .workflows import workflow_pages
from .graph import graph_pages
from .analytics import analytics_pages
from .recommendations import recommendation_pages
from .audit import audit_pages
from .lineage import lineage_pages
from .reports import report_pages
from .system_health import system_health_pages

__all__ = [
    "event_pages", "timeline_pages", "workflow_pages", "graph_pages", "analytics_pages",
    "recommendation_pages", "audit_pages", "lineage_pages", "report_pages",
    "system_health_pages",
]
