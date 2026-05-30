"""Finding lifecycle state machine.

A mostly-forward DAG with governed revise/supersede edges; ARCHIVED is terminal.
Every transition is validated; forbidden transitions raise ``FindingLifecycleError``
and are never silently allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import FINDING_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH
from ..models.domain import FindingStatus

F = FindingStatus

FINDING_TRANSITIONS: Mapping[FindingStatus, frozenset] = {
    F.CREATED: frozenset({F.DRAFT, F.ARCHIVED}),
    F.DRAFT: frozenset({F.UNDER_REVIEW, F.ARCHIVED}),
    F.UNDER_REVIEW: frozenset({F.CONFIRMED, F.DRAFT, F.ARCHIVED}),       # send back to draft
    F.CONFIRMED: frozenset({F.REVISED, F.SUPERSEDED, F.CLOSED, F.ARCHIVED}),
    F.REVISED: frozenset({F.UNDER_REVIEW, F.SUPERSEDED, F.ARCHIVED}),
    F.SUPERSEDED: frozenset({F.CLOSED, F.ARCHIVED}),
    F.CLOSED: frozenset({F.ARCHIVED}),
    F.ARCHIVED: frozenset(),  # terminal
}

FINDING_TERMINAL_STATES = frozenset({F.ARCHIVED})


class FindingLifecycleError(RuntimeError):
    """Raised on an attempted forbidden finding transition."""


def is_allowed_transition(src: FindingStatus, dst: FindingStatus) -> bool:
    return dst in FINDING_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class FindingTransitionRecord:
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


class FindingLifecycle:
    version = FINDING_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(status: FindingStatus) -> frozenset:
        return FINDING_TRANSITIONS.get(status, frozenset())

    @staticmethod
    def is_terminal(status: FindingStatus) -> bool:
        return status in FINDING_TERMINAL_STATES

    def transition(self, current: FindingStatus, target: FindingStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> FindingTransitionRecord:
        if not isinstance(target, FindingStatus):
            raise FindingLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise FindingLifecycleError(f"no-op transition {current.value} -> {target.value}")
        if not is_allowed_transition(current, target):
            raise FindingLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return FindingTransitionRecord(from_state=current.value, to_state=target.value, reason=reason,
                                       lifecycle_version=self.version, created_at=created_at)
