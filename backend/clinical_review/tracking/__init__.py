"""``backend/clinical_review/tracking`` — review progress tracking (V2-P2).

Derives progress, milestones, duration, revisions, reopen/completion events from a
Review + its audit log, and builds a reproducible tracking report.
"""

from __future__ import annotations

from .tracking import ReviewTracker

__all__ = ["ReviewTracker"]
