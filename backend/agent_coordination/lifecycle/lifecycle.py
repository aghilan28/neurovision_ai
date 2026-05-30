"""Agent lifecycle state machine (V4-P5).

Legal transitions form a mostly-forward DAG with a governed suspend/resume pair and
a universal path to ARCHIVED (terminal). Every transition is validated against this
table; a forbidden transition raises ``AgentLifecycleError`` (stop-and-remediate)
and is never silently allowed.

States: PROPOSED -> DRAFT -> UNDER_REVIEW -> APPROVED -> AVAILABLE -> {SUSPENDED,
RETIRED} -> ARCHIVED. The move into AVAILABLE (and the other governed transitions)
requires policy-governed approval (enforced by the service). AVAILABLE means "this
participant may be assigned/authorized", never "this participant is acting" — agents
describe capability and never possess autonomous authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import AGENT_LIFECYCLE_VERSION, DETERMINISTIC_EPOCH


class AgentLifecycleState(str, Enum):
    PROPOSED = "proposed"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    AVAILABLE = "available"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    ARCHIVED = "archived"


S = AgentLifecycleState

# allowed transitions: from -> set(to)
AGENT_TRANSITIONS: Mapping[AgentLifecycleState, frozenset] = {
    S.PROPOSED: frozenset({S.DRAFT, S.ARCHIVED}),
    S.DRAFT: frozenset({S.UNDER_REVIEW, S.ARCHIVED}),
    S.UNDER_REVIEW: frozenset({S.APPROVED, S.DRAFT, S.ARCHIVED}),       # revise -> draft
    S.APPROVED: frozenset({S.AVAILABLE, S.SUSPENDED, S.ARCHIVED}),
    S.AVAILABLE: frozenset({S.SUSPENDED, S.RETIRED, S.ARCHIVED}),
    S.SUSPENDED: frozenset({S.AVAILABLE, S.RETIRED, S.ARCHIVED}),       # resume -> available
    S.RETIRED: frozenset({S.ARCHIVED}),
    S.ARCHIVED: frozenset(),                                           # terminal
}

TERMINAL_STATES = frozenset({S.ARCHIVED})

# transitions that require policy-governed approval (Agent<->Policy integration).
GOVERNED_TRANSITIONS: Mapping[AgentLifecycleState, str] = {
    S.APPROVED: "agent_approval",
    S.AVAILABLE: "agent_availability",
    S.SUSPENDED: "agent_suspension",
    S.RETIRED: "agent_retirement",
}


class AgentLifecycleError(RuntimeError):
    """Raised on an attempted forbidden agent lifecycle transition."""


def is_allowed_transition(src: AgentLifecycleState, dst: AgentLifecycleState) -> bool:
    return dst in AGENT_TRANSITIONS.get(src, frozenset())


@dataclass(frozen=True)
class AgentTransitionRecord:
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


class AgentLifecycle:
    """The agent lifecycle state machine (stateless validator/transitioner)."""

    version = AGENT_LIFECYCLE_VERSION

    @staticmethod
    def allowed_targets(state: AgentLifecycleState) -> frozenset:
        return AGENT_TRANSITIONS.get(state, frozenset())

    @staticmethod
    def is_terminal(state: AgentLifecycleState) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def requires_policy(target: AgentLifecycleState) -> bool:
        return target in GOVERNED_TRANSITIONS

    @staticmethod
    def policy_hook(target: AgentLifecycleState) -> str | None:
        return GOVERNED_TRANSITIONS.get(target)

    def transition(self, current: AgentLifecycleState, target: AgentLifecycleState,
                   reason: str = "", created_at: str = DETERMINISTIC_EPOCH
                   ) -> AgentTransitionRecord:
        """Validate + produce a transition record, or raise on a forbidden move."""
        if not isinstance(target, AgentLifecycleState):
            raise AgentLifecycleError(f"unknown target state {target!r}")
        if current == target:
            raise AgentLifecycleError(
                f"no-op transition {current.value} -> {target.value} is not allowed")
        if not is_allowed_transition(current, target):
            raise AgentLifecycleError(
                f"forbidden transition {current.value} -> {target.value} "
                f"(allowed: {sorted(t.value for t in self.allowed_targets(current))})")
        return AgentTransitionRecord(from_state=current.value, to_state=target.value,
                                     reason=reason, lifecycle_version=self.version,
                                     created_at=created_at)
