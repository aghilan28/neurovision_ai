"""Execution lifecycle state machine (V4-P6).

Legal transitions form a mostly-forward DAG with governed pause/resume and
block/unblock pairs and a universal path to ARCHIVED (terminal). Every transition is
validated against this table; a forbidden transition raises ``ExecutionLifecycle
Error`` (stop-and-remediate) and is never silently allowed.

States: PROPOSED -> QUEUED -> AUTHORIZED -> ACTIVE -> {PAUSED, BLOCKED, COMPLETED,
TERMINATED} -> ARCHIVED. The move into ACTIVE requires authorization (policy-governed)
— execution is the *governed progression of approved work*, never autonomous action.
PAUSED/BLOCKED are operational states that resume to ACTIVE; TERMINATED/COMPLETED are
governed terminal-ish states that archive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EXECUTION_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


class ExecutionLifecycleState(str, Enum):
    PROPOSED = "proposed"
    QUEUED = "queued"
    AUTHORIZED = "authorized"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ARCHIVED = "archived"


S = ExecutionLifecycleState

# allowed transitions: from -> set(to)
EXECUTION_TRANSITIONS: Mapping[ExecutionLifecycleState, frozenset] = {
    S.PROPOSED: frozenset({S.QUEUED, S.TERMINATED, S.ARCHIVED}),
    S.QUEUED: frozenset({S.AUTHORIZED, S.TERMINATED, S.ARCHIVED}),
    S.AUTHORIZED: frozenset({S.ACTIVE, S.TERMINATED, S.ARCHIVED}),
    S.ACTIVE: frozenset({S.PAUSED, S.BLOCKED, S.COMPLETED, S.TERMINATED}),
    S.PAUSED: frozenset({S.ACTIVE, S.TERMINATED, S.ARCHIVED}),          # resume -> active
    S.BLOCKED: frozenset({S.ACTIVE, S.TERMINATED, S.ARCHIVED}),         # unblock -> active
    S.COMPLETED: frozenset({S.ARCHIVED}),
    S.TERMINATED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),                                           # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})

# transitions that require policy-governed authorization/approval.
# ACTIVE is the critical gate: execution cannot become ACTIVE without authorization.
GOVERNED_TRANSITIONS: Mapping[ExecutionLifecycleState, str] = {
    S.AUTHORIZED: "execution_authorization",
    S.ACTIVE: "execution_activation",
    S.COMPLETED: "execution_completion",
    S.TERMINATED: "execution_termination",
}


class ExecutionLifecycleError(RuntimeError):
    """Raised on an attempted forbidden execution lifecycle transition."""


def is_allowed_transition(src: ExecutionLifecycleState, dst: ExecutionLifecycleState) -> bool:
    return dst in EXECUTION_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class ExecutionTransitionRecord:
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


class ExecutionLifecycle:
    """The execution lifecycle state machine (stateless validator/transitioner)."""

    version = EXECUTION_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(state: ExecutionLifecycleState) -> frozenset:
        return EXECUTION_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def is_terminal(state: ExecutionLifecycleState) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def requires_policy(target: ExecutionLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    @staticmethod
    def policy_hook(target: ExecutionLifecycleState) -> str | None:
        return GOVERNED_TRANSITIONS.get(target)

    def transition(self, current: ExecutionLifecycleState, target: ExecutionLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH
                   ) -> ExecutionTransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, ExecutionLifecycleState):
            raise ExecutionLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise ExecutionLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise ExecutionLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return ExecutionTransitionRecord(from_state=current.value, to_state=target.value,
                                         reason=reason, lifecycle_version=self.version,
                                         created_at=created_at)
