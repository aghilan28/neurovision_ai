"""Case lifecycle state machine.

Legal transitions form a mostly-forward DAG with two governed "reopen" edges and a
universal path to ARCHIVED. ARCHIVED is terminal. Every transition is validated
against this table; a forbidden transition raises ``LifecycleError`` (stop-and-
remediate) and is never silently allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import CASE_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH
from ..models.domain import CaseStatus

S = CaseStatus

# allowed transitions: from -> set(to)
CASE_TRANSITIONS: Mapping[CaseStatus, frozenset] = {
    S.CREATED: frozenset({S.INGESTED, S.ARCHIVED}),
    S.INGESTED: frozenset({S.PROCESSING, S.ARCHIVED}),
    S.PROCESSING: frozenset({S.READY_FOR_REVIEW, S.ARCHIVED}),
    S.READY_FOR_REVIEW: frozenset({S.UNDER_REVIEW, S.ARCHIVED}),
    S.UNDER_REVIEW: frozenset({S.REVIEWED, S.READY_FOR_REVIEW, S.ARCHIVED}),  # reopen -> ready
    S.REVIEWED: frozenset({S.CLOSED, S.UNDER_REVIEW, S.ARCHIVED}),            # reopen -> under_review
    S.CLOSED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),  # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})


class LifecycleError(RuntimeError):
    """Raised on an attempted forbidden lifecycle transition."""


def is_allowed_transition(src: CaseStatus, dst: CaseStatus) -> bool:
    return dst in CASE_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class TransitionRecord:
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


class CaseLifecycle:
    """The case lifecycle state machine (stateless validator/transitioner)."""

    version = CASE_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(status: CaseStatus) -> frozenset:
        return CASE_TRANSITIONS.get(status, frozenset())

    @staticmethod
    def is_terminal(status: CaseStatus) -> bool:
        return status in TERMINAL_STATES

    def transition(self, current: CaseStatus, target: CaseStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> TransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, CaseStatus):
            raise LifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise LifecycleError(f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise LifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return TransitionRecord(from_state=current.value, to_state=target.value, reason=reason,
                                lifecycle_version=self.version, created_at=created_at)
