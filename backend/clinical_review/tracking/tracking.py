"""Review tracking: progress, milestones, duration, revisions, events.

All values are derived deterministically from the Review aggregate and its audit
log (the single source of truth) — tracking never holds independent state.
"""

from __future__ import annotations

from typing import Any

from ..version import REVIEW_TRACKING_VERSION
from ..models.domain import ReviewStatus

# linear milestone order used to compute a 0..1 progress fraction
_MILESTONES = [
    ReviewStatus.CREATED, ReviewStatus.ASSIGNED, ReviewStatus.IN_PROGRESS,
    ReviewStatus.PENDING_CONFIRMATION, ReviewStatus.COMPLETED, ReviewStatus.CLOSED,
]


class ReviewTracker:
    version = REVIEW_TRACKING_VERSION

    @staticmethod
    def summarize(review: Any, audit_log: Any) -> dict:
        events = audit_log.events()
        status_changes = [e for e in events if e.kind == "status_change"]
        to_states = [e.payload.get("to_state") for e in status_changes]
        reopen_events = sum(1 for s in to_states if s == ReviewStatus.REOPENED.value)
        completion_events = sum(1 for s in to_states if s == ReviewStatus.COMPLETED.value)

        # milestones reached = the linear milestones whose state appears in history
        reached = [m.value for m in _MILESTONES
                   if m.value in to_states or m == ReviewStatus.CREATED]
        # progress fraction by current status position on the linear track
        cur = review.status
        if cur in _MILESTONES:
            progress = _MILESTONES.index(cur) / (len(_MILESTONES) - 1)
        elif cur == ReviewStatus.REOPENED:
            progress = _MILESTONES.index(ReviewStatus.IN_PROGRESS) / (len(_MILESTONES) - 1)
        elif cur == ReviewStatus.ARCHIVED:
            progress = 1.0
        else:
            progress = 0.0

        closed_sessions = [s for s in review.sessions if not s.is_open]
        return {
            "review_tracking_version": REVIEW_TRACKING_VERSION,
            "status": cur.value,
            "progress": round(float(progress), 4),
            "milestones_reached": reached,
            "n_sessions": len(review.sessions),
            "n_completed_sessions": len(closed_sessions),
            "duration_transitions": review.transition_count,
            "revisions": reopen_events,
            "reopen_events": reopen_events,
            "completion_events": completion_events,
            "is_complete": cur in (ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED),
        }

    @staticmethod
    def report(review: Any, audit_log: Any) -> dict:
        return {
            "report_type": "review_progress",
            "review_tracking_version": REVIEW_TRACKING_VERSION,
            "review_id": review.review_id,
            "case_id": review.case_id,
            "tracking": ReviewTracker.summarize(review, audit_log),
        }
