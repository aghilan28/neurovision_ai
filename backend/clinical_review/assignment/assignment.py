"""Review assignment management.

Assignments are immutable values; reassignment closes the prior assignment and
creates a new active one (history preserved on the Review). ``escalate`` is a
**forward hook**: it bumps an escalation level for future routing logic but performs
no operational action in V2 (no notifications, no auto-reassignment).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ml.provenance import content_id  # allowed: backend -> ml

from ..version import DETERMINISTIC_EPOCH
from ..models.domain import ReviewAssignment

VALID_PRIORITIES = ("routine", "urgent", "stat")


class AssignmentError(ValueError):
    """Raised on an invalid assignment operation."""


class AssignmentManager:
    @staticmethod
    def new_assignment(*, review_id: str, case_id: str, assignee: str, index: int,
                       priority: str = "routine", reason: str = "",
                       date: str = DETERMINISTIC_EPOCH) -> ReviewAssignment:
        if not assignee:
            raise AssignmentError("assignee must be non-empty")
        if priority not in VALID_PRIORITIES:
            raise AssignmentError(f"priority must be one of {VALID_PRIORITIES}")
        assignment_id = content_id("assignment", {"review_id": review_id, "assignee": assignee,
                                                  "index": index})
        return ReviewAssignment(assignment_id=assignment_id, review_id=review_id, case_id=case_id,
                                assignee=assignee, assignment_date=date, priority=priority,
                                status="active", reason=reason)

    @staticmethod
    def reassign(prior: ReviewAssignment, *, new_assignee: str, index: int,
                 reason: str = "", date: str = DETERMINISTIC_EPOCH) -> tuple[ReviewAssignment, ReviewAssignment]:
        closed = replace(prior, status="reassigned")
        fresh = AssignmentManager.new_assignment(
            review_id=prior.review_id, case_id=prior.case_id, assignee=new_assignee,
            index=index, priority=prior.priority, reason=reason, date=date)
        return closed, fresh

    @staticmethod
    def escalate(assignment: ReviewAssignment) -> ReviewAssignment:
        """Forward escalation hook (inert in V2): bumps the escalation level only."""
        return replace(assignment, escalation_level=assignment.escalation_level + 1)
