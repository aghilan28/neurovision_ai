"""``backend/clinical_review/assignment`` — assignment framework (V2-P2).

Tracks assignee, date, priority, status, case, review, reason, and history, with an
inert forward **escalation hook** (no routing/notification logic in V2).
"""

from __future__ import annotations

from .assignment import AssignmentManager, VALID_PRIORITIES, AssignmentError

__all__ = ["AssignmentManager", "VALID_PRIORITIES", "AssignmentError"]
