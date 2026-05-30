"""Plan lifecycle state machine (V4-P3).

Legal transitions form a mostly-forward DAG with a governed suspend/resume pair and
a universal path to ARCHIVED (terminal). Every transition is validated against this
table; a forbidden transition raises ``PlanLifecycleError`` (stop-and-remediate) and
is never silently allowed.

States: PROPOSED -> DRAFT -> UNDER_REVIEW -> APPROVED -> READY -> {SUSPENDED,
COMPLETED} -> ARCHIVED. The move into READY (and the other governed transitions)
additionally requires policy-governed approval (enforced by the service). A plan is
an intent structure: READY means "ready for work to be derived", never "executing".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import PLAN_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


class PlanLifecycleState(str, Enum):
    PROPOSED = "proposed"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    READY = "ready"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"


S = PlanLifecycleState

# allowed transitions: from -> set(to)
PLAN_TRANSITIONS: Mapping[PlanLifecycleState, frozenset] = {
    S.PROPOSED: frozenset({S.DRAFT, S.ARCHIVED}),
    S.DRAFT: frozenset({S.UNDER_REVIEW, S.ARCHIVED}),
    S.UNDER_REVIEW: frozenset({S.APPROVED, S.DRAFT, S.ARCHIVED}),       # revise -> draft
    S.APPROVED: frozenset({S.READY, S.SUSPENDED, S.ARCHIVED}),
    S.READY: frozenset({S.SUSPENDED, S.COMPLETED, S.ARCHIVED}),
    S.SUSPENDED: frozenset({S.READY, S.ARCHIVED}),                     # resume -> ready
    S.COMPLETED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),                                           # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})

# transitions that require policy-governed approval (Plan<->Policy integration).
# Mapped to the policy hook name the service evaluates before allowing the move.
GOVERNED_TRANSITIONS: Mapping[PlanLifecycleState, str] = {
    S.APPROVED: "plan_approval",
    S.READY: "plan_readiness",
    S.SUSPENDED: "plan_suspension",
    S.COMPLETED: "plan_completion",
}


class PlanLifecycleError(RuntimeError):
    """Raised on an attempted forbidden plan lifecycle transition."""


def is_allowed_transition(src: PlanLifecycleState, dst: PlanLifecycleState) -> bool:
    return dst in PLAN_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class PlanTransitionRecord:
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


class PlanLifecycle:
    """The plan lifecycle state machine (stateless validator/transitioner)."""

    version = PLAN_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(state: PlanLifecycleState) -> frozenset:
        return PLAN_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def is_terminal(state: PlanLifecycleState) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def requires_policy(target: PlanLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    @staticmethod
    def policy_hook(target: PlanLifecycleState) -> str | None:
        return GOVERNED_TRANSITIONS.get(target)

    def transition(self, current: PlanLifecycleState, target: PlanLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH) -> PlanTransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, PlanLifecycleState):
            raise PlanLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise PlanLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise PlanLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return PlanTransitionRecord(from_state=current.value, to_state=target.value,
                                    reason=reason, lifecycle_version=self.version,
                                    created_at=created_at)
