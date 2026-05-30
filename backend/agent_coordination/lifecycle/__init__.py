"""Agent lifecycle package (V4-P5)."""

from __future__ import annotations

from .lifecycle import (
    AgentLifecycleState, AgentLifecycle, AgentLifecycleError, AgentTransitionRecord,
    AGENT_TRANSITIONS, TERMINAL_STATES, GOVERNED_TRANSITIONS, is_allowed_transition,
)

__all__ = [
    "AgentLifecycleState", "AgentLifecycle", "AgentLifecycleError", "AgentTransitionRecord",
    "AGENT_TRANSITIONS", "TERMINAL_STATES", "GOVERNED_TRANSITIONS", "is_allowed_transition",
]
