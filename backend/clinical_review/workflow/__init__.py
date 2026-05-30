"""``backend/clinical_review/workflow`` — review lifecycle state machine (V2-P2).

Governs legal transitions between review states; forbidden transitions are blocked;
each accepted transition yields a record for the audit log.
"""

from __future__ import annotations

from .workflow import (
    REVIEW_TRANSITIONS,
    REVIEW_TERMINAL_STATES,
    ReviewLifecycle,
    ReviewTransitionRecord,
    ReviewLifecycleError,
    is_allowed_transition,
)

__all__ = [
    "REVIEW_TRANSITIONS",
    "REVIEW_TERMINAL_STATES",
    "ReviewLifecycle",
    "ReviewTransitionRecord",
    "ReviewLifecycleError",
    "is_allowed_transition",
]
