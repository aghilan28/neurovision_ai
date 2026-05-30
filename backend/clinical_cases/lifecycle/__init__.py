"""``backend/clinical_cases/lifecycle`` — case lifecycle state machine (V2-P1).

Governs the legal transitions between case states. Every transition is validated;
forbidden transitions are blocked; each accepted transition yields a transition
record for the audit log.
"""

from __future__ import annotations

from .lifecycle import (
    CASE_TRANSITIONS,
    TERMINAL_STATES,
    CaseLifecycle,
    TransitionRecord,
    LifecycleError,
    is_allowed_transition,
)

__all__ = [
    "CASE_TRANSITIONS",
    "TERMINAL_STATES",
    "CaseLifecycle",
    "TransitionRecord",
    "LifecycleError",
    "is_allowed_transition",
]
