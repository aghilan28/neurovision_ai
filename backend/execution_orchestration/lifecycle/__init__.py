"""Execution lifecycle package (V4-P6)."""

from __future__ import annotations

from .lifecycle import (
    ExecutionLifecycleState, ExecutionLifecycle, ExecutionLifecycleError,
    ExecutionTransitionRecord, EXECUTION_TRANSITIONS, TERMINAL_STATES, GOVERNED_TRANSITIONS,
    is_allowed_transition,
)

__all__ = [
    "ExecutionLifecycleState", "ExecutionLifecycle", "ExecutionLifecycleError",
    "ExecutionTransitionRecord", "EXECUTION_TRANSITIONS", "TERMINAL_STATES",
    "GOVERNED_TRANSITIONS", "is_allowed_transition",
]
