"""Review lifecycle state machine.

A mostly-forward DAG with governed reopen edges and a universal path to ARCHIVED
(terminal). Every transition is validated against this table; forbidden transitions
raise ``ReviewLifecycleError`` and are never silently allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import REVIEW_WORKFLOW_VERSION, DETERMINISTIC_EPOCH
from ..models.domain import ReviewStatus

R = ReviewStatus

REVIEW_TRANSITIONS: Mapping[ReviewStatus, frozenset] = {
    R.CREATED: frozenset({R.ASSIGNED, R.ARCHIVED}),
    R.ASSIGNED: frozenset({R.IN_PROGRESS, R.ARCHIVED}),
    R.IN_PROGRESS: frozenset({R.PENDING_CONFIRMATION, R.ARCHIVED}),
    R.PENDING_CONFIRMATION: frozenset({R.COMPLETED, R.IN_PROGRESS, R.ARCHIVED}),  # send back
    R.COMPLETED: frozenset({R.CLOSED, R.REOPENED, R.ARCHIVED}),
    R.REOPENED: frozenset({R.IN_PROGRESS, R.ARCHIVED}),
    R.CLOSED: frozenset({R.REOPENED, R.ARCHIVED}),
    R.ARCHIVED: frozenset(),  # terminal
}

REVIEW_TERMINAL_STATES = frozenset({R.ARCHIVED})


class ReviewLifecycleError(RuntimeError):
    """Raised on an attempted forbidden review transition."""


def is_allowed_transition(src: ReviewStatus, dst: ReviewStatus) -> bool:
    return dst in REVIEW_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class ReviewTransitionRecord:
    from_state: str
    to_state: str
    reason: str
    workflow_version: str
    created_at: str = DETERMINISTIC_EPOCH

    def signature(self) -> str:
        return hash_obj({"from": self.from_state, "to": self.to_state, "reason": self.reason,
                         "workflow_version": self.workflow_version})

    def to_dict(self) -> dict:
        return {"from_state": self.from_state, "to_state": self.to_state, "reason": self.reason,
                "workflow_version": self.workflow_version, "created_at": self.created_at,
                "signature": self.signature()}


class ReviewLifecycle:
    version = REVIEW_WORKFLOW_VERSION

    @staticmethod
    def allowed_targets(status: ReviewStatus) -> frozenset:
        return REVIEW_TRANSITIONS.get(status, frozenset())

    @staticmethod
    def is_terminal(status: ReviewStatus) -> bool:
        return status in REVIEW_TERMINAL_STATES

    def transition(self, current: ReviewStatus, target: ReviewStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> ReviewTransitionRecord:
        if not isinstance(target, ReviewStatus):
            raise ReviewLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise ReviewLifecycleError(f"no-op transition {current.value} -> {target.value}")
        if not is_allowed_transition(current, target):
            raise ReviewLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return ReviewTransitionRecord(from_state=current.value, to_state=target.value,
                                      reason=reason, workflow_version=self.version, created_at=created_at)
