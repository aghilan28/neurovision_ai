"""Policy lifecycle state machine (V4-P2).

Governs a policy's own lifecycle: DRAFT -> UNDER_REVIEW -> APPROVED -> ACTIVE ->
{SUSPENDED, DEPRECATED}. A policy may only evaluate requests when ACTIVE, and no
policy becomes ACTIVE without governance approval (enforced by the service). Every
transition is validated; forbidden transitions raise ``PolicyLifecycleError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import POLICY_GOVERNANCE_VERSION, DETERMINISTIC_EPOCH
from .taxonomy import PolicyLifecycleState

S = PolicyLifecycleState

POLICY_TRANSITIONS: Mapping[PolicyLifecycleState, frozenset] = {
    S.DRAFT: frozenset({S.UNDER_REVIEW, S.DEPRECATED}),
    S.UNDER_REVIEW: frozenset({S.APPROVED, S.DRAFT, S.DEPRECATED}),       # revise -> draft
    S.APPROVED: frozenset({S.ACTIVE, S.SUSPENDED, S.DEPRECATED}),
    S.ACTIVE: frozenset({S.SUSPENDED, S.DEPRECATED}),
    S.SUSPENDED: frozenset({S.ACTIVE, S.DEPRECATED}),                    # reactivate -> active
    S.DEPRECATED: frozenset(),                                          # terminal
}

TERMINAL_STATES = frozenset({S.DEPRECATED})

# transitions requiring governance approval
GOVERNED_TRANSITIONS = frozenset({S.APPROVED, S.ACTIVE})


class PolicyLifecycleError(RuntimeError):
    """Raised on an attempted forbidden policy lifecycle transition."""


def is_allowed_transition(src: PolicyLifecycleState, dst: PolicyLifecycleState) -> bool:
    return dst in POLICY_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class PolicyTransitionRecord:
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


class PolicyLifecycle:
    """The policy lifecycle state machine (stateless validator/transitioner)."""

    version = POLICY_GOVERNANCE_VERSION

    @staticmethod
    def allowed_targets(state: PolicyLifecycleState) -> frozenset:
        return POLICY_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def requires_governance(target: PolicyLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    def transition(self, current: PolicyLifecycleState, target: PolicyLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH
                   ) -> PolicyTransitionRecord:
        if not isinstance(target, PolicyLifecycleState):
            raise PolicyLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise PolicyLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise PolicyLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return PolicyTransitionRecord(from_state=current.value, to_state=target.value,
                                      reason=reason, lifecycle_version=self.version,
                                      created_at=created_at)
