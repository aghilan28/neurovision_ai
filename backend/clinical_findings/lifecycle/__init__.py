"""``backend/clinical_findings/lifecycle`` — finding lifecycle state machine (V2-P3)."""

from __future__ import annotations

from .lifecycle import (
    FINDING_TRANSITIONS,
    FINDING_TERMINAL_STATES,
    FindingLifecycle,
    FindingTransitionRecord,
    FindingLifecycleError,
    is_allowed_transition,
)

__all__ = [
    "FINDING_TRANSITIONS",
    "FINDING_TERMINAL_STATES",
    "FindingLifecycle",
    "FindingTransitionRecord",
    "FindingLifecycleError",
    "is_allowed_transition",
]
