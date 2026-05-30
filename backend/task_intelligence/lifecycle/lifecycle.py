"""Task lifecycle state machine (V4-P4).

Legal transitions form a mostly-forward DAG with a governed block/resume pair and a
universal path to ARCHIVED (terminal). Every transition is validated against this
table; a forbidden transition raises ``TaskLifecycleError`` (stop-and-remediate) and
is never silently allowed.

States: PROPOSED -> DRAFT -> UNDER_REVIEW -> APPROVED -> READY -> {BLOCKED,
COMPLETED} -> ARCHIVED. The move into READY (and APPROVED, COMPLETED) requires
policy-governed approval (enforced by the service). BLOCKED is a non-governed
*operational* state (a READY task whose dependencies are not yet satisfied); a task
*describes* work and never executes it — BLOCKED records structure, not execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import TASK_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


class TaskLifecycleState(str, Enum):
    PROPOSED = "proposed"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    READY = "ready"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


S = TaskLifecycleState

# allowed transitions: from -> set(to)
TASK_TRANSITIONS: Mapping[TaskLifecycleState, frozenset] = {
    S.PROPOSED: frozenset({S.DRAFT, S.ARCHIVED}),
    S.DRAFT: frozenset({S.UNDER_REVIEW, S.ARCHIVED}),
    S.UNDER_REVIEW: frozenset({S.APPROVED, S.DRAFT, S.ARCHIVED}),       # revise -> draft
    S.APPROVED: frozenset({S.READY, S.ARCHIVED}),
    S.READY: frozenset({S.BLOCKED, S.COMPLETED, S.ARCHIVED}),
    S.BLOCKED: frozenset({S.READY, S.ARCHIVED}),                       # unblock -> ready
    S.COMPLETED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),                                           # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})

# transitions that require policy-governed approval (Task<->Policy integration).
# BLOCKED is intentionally NOT governed — it is an operational dependency state.
GOVERNED_TRANSITIONS: Mapping[TaskLifecycleState, str] = {
    S.APPROVED: "task_approval",
    S.READY: "task_readiness",
    S.COMPLETED: "task_completion",
}


class TaskLifecycleError(RuntimeError):
    """Raised on an attempted forbidden task lifecycle transition."""


def is_allowed_transition(src: TaskLifecycleState, dst: TaskLifecycleState) -> bool:
    return dst in TASK_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class TaskTransitionRecord:
    """A validated lifecycle transition (fed to the audit log)."""

    from_state: str
    to_state: str
    reason: str
    lifecycle_version: str
    created_at: str = DETERMINISTIC_EPOCH

    def signature(self) -> str:
        return hash_obj({"from": self.from_state, "to": self.to_state, "reason": self.reason,
                         "lifecycle_version": self.lifecycle_version})

    def to_dict(self) -> dict:
        return {"from_state": self.from_state, "to_state": self.to_state, "reason": self.reason,
                "lifecycle_version": self.lifecycle_version, "created_at": self.created_at,
                "signature": self.signature()}


class TaskLifecycle:
    """The task lifecycle state machine (stateless validator/transitioner)."""

    version = TASK_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(state: TaskLifecycleState) -> frozenset:
        return TASK_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def is_terminal(state: TaskLifecycleState) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def requires_policy(target: TaskLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    @staticmethod
    def policy_hook(target: TaskLifecycleState) -> str | None:
        return GOVERNED_TRANSITIONS.get(target)

    def transition(self, current: TaskLifecycleState, target: TaskLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH) -> TaskTransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, TaskLifecycleState):
            raise TaskLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise TaskLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise TaskLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return TaskTransitionRecord(from_state=current.value, to_state=target.value,
                                    reason=reason, lifecycle_version=self.version,
                                    created_at=created_at)
