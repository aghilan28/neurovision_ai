"""Goal lifecycle state machine (V4-P1).

Legal transitions form a mostly-forward DAG with a governed suspend/resume pair and
a universal path to ARCHIVED (terminal). Every transition is validated against this
table; a forbidden transition raises ``GoalLifecycleError`` (stop-and-remediate) and
is never silently allowed.

States: PROPOSED -> DRAFT -> UNDER_REVIEW -> APPROVED -> ACTIVE -> {SUSPENDED,
COMPLETED} -> ARCHIVED. The move into ACTIVE additionally requires policy-governed
approval (enforced by the service, not just the table).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import GOAL_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


class GoalLifecycleState(str, Enum):
    PROPOSED = "proposed"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"


S = GoalLifecycleState

# allowed transitions: from -> set(to)
GOAL_TRANSITIONS: Mapping[GoalLifecycleState, frozenset] = {
    S.PROPOSED: frozenset({S.DRAFT, S.ARCHIVED}),
    S.DRAFT: frozenset({S.UNDER_REVIEW, S.ARCHIVED}),
    S.UNDER_REVIEW: frozenset({S.APPROVED, S.DRAFT, S.ARCHIVED}),       # revise -> draft
    S.APPROVED: frozenset({S.ACTIVE, S.SUSPENDED, S.ARCHIVED}),
    S.ACTIVE: frozenset({S.SUSPENDED, S.COMPLETED, S.ARCHIVED}),
    S.SUSPENDED: frozenset({S.ACTIVE, S.ARCHIVED}),                     # resume -> active
    S.COMPLETED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),                                           # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})

# transitions that require policy-governed approval (Goal<->Policy integration).
# Mapped to the policy hook name the service evaluates before allowing the move.
GOVERNED_TRANSITIONS: Mapping[GoalLifecycleState, str] = {
    S.APPROVED: "goal_approval",
    S.ACTIVE: "goal_activation",
    S.SUSPENDED: "goal_suspension",
    S.COMPLETED: "goal_completion",
}


class GoalLifecycleError(RuntimeError):
    """Raised on an attempted forbidden goal lifecycle transition."""


def is_allowed_transition(src: GoalLifecycleState, dst: GoalLifecycleState) -> bool:
    return dst in GOAL_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class GoalTransitionRecord:
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


class GoalLifecycle:
    """The goal lifecycle state machine (stateless validator/transitioner)."""

    version = GOAL_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(state: GoalLifecycleState) -> frozenset:
        return GOAL_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def is_terminal(state: GoalLifecycleState) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def requires_policy(target: GoalLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    @staticmethod
    def policy_hook(target: GoalLifecycleState) -> str | None:
        return GOVERNED_TRANSITIONS.get(target)

    def transition(self, current: GoalLifecycleState, target: GoalLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH) -> GoalTransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, GoalLifecycleState):
            raise GoalLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise GoalLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise GoalLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return GoalTransitionRecord(from_state=current.value, to_state=target.value,
                                    reason=reason, lifecycle_version=self.version,
                                    created_at=created_at)
