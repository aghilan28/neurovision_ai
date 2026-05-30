"""Workspace builders — each renders Page view-models from the snapshot."""

from __future__ import annotations

from .cases import case_pages
from .reviews import review_pages
from .findings import finding_pages
from .knowledge import knowledge_pages
from .intelligence import intelligence_pages
from .decision_support import decision_pages
from .audit import audit_pages
from .lineage import lineage_pages
from .reports import report_pages
from .dashboards import dashboard_pages

__all__ = [
    "case_pages", "review_pages", "finding_pages", "knowledge_pages", "intelligence_pages",
    "decision_pages", "audit_pages", "lineage_pages", "report_pages", "dashboard_pages",
]
