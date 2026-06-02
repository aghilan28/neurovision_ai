"""Governed-entity observation (V4-P7) — the read-only source view.

Governance intelligence is derived from the already-governed artifacts. This module
normalizes each governed entity (goal / policy / constraint / plan / task / agent /
execution) into a single uniform :class:`GovernedObservation` so the approval,
violation, escalation, risk, analytics, and monitoring engines can reason about them
identically. **Observation reads; it never mutates** the governed entity.

The normalization reads each entity's governance projection defensively (goals/plans/
tasks/agents expose ``approval_state``/``approval_history``; executions expose
``authorization_state``/``authorization_history``), plus its lifecycle state, lineage
node, and policy references. Nothing is recomputed — the values are exactly those the
backend already recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .domain import GovernedKind, GOVERNED_KINDS

# the lifecycle states that mean an entity is "live" (admitted past approval).
_LIVE_STATES: frozenset[str] = frozenset({
    "active", "available", "ready", "completed", "approved", "authorized",
})

# id attribute name per governed kind.
_ID_ATTR: dict[str, str] = {
    GovernedKind.GOAL: "goal_id", GovernedKind.POLICY: "policy_id",
    GovernedKind.CONSTRAINT: "constraint_id", GovernedKind.PLAN: "plan_id",
    GovernedKind.TASK: "task_id", GovernedKind.AGENT: "agent_id",
    GovernedKind.EXECUTION: "execution_id",
}

# decisions that count as a positive (granting) governance decision.
_POSITIVE_DECISIONS: frozenset[str] = frozenset({
    "permitted", "approved", "authorized", "conditional_approval",
})


@dataclass(frozen=True)
class GovernedObservation:
    """A uniform, read-only projection of one governed entity's governance state."""

    kind: str
    entity_id: str
    approval_state: str
    decision: str
    authority: Optional[str]
    history: tuple[dict, ...]
    escalation_required: bool
    escalated: bool
    policy_references: tuple[str, ...]
    state: str
    lineage_id: Optional[str]
    live: bool

    @property
    def latency_steps(self) -> int:
        """Logical approval latency: number of governance events recorded."""
        return len(self.history)

    @property
    def approved(self) -> bool:
        return self.approval_state in ("approved", "authorized")

    @property
    def denied(self) -> bool:
        return self.approval_state in ("rejected", "denied")

    @property
    def pending(self) -> bool:
        return self.approval_state == "pending"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "entity_id": self.entity_id,
                "approval_state": self.approval_state, "decision": self.decision,
                "authority": self.authority, "history": [dict(h) for h in self.history],
                "escalation_required": self.escalation_required, "escalated": self.escalated,
                "policy_references": list(self.policy_references), "state": self.state,
                "lineage_id": self.lineage_id, "live": self.live,
                "latency_steps": self.latency_steps, "approved": self.approved}


def _state_value(record: Any) -> str:
    st = getattr(record, "state", None)
    if st is None:
        return ""
    return getattr(st, "value", str(st))


def observe_record(kind: str, record: Any) -> GovernedObservation:
    """Normalize one governed entity into a :class:`GovernedObservation` (read-only)."""
    if kind not in GOVERNED_KINDS:
        raise ValueError(f"unknown governed kind {kind!r}")
    gov = getattr(record, "governance", None)

    # approval / authorization state + history (defensive across entity kinds)
    approval_state = (getattr(gov, "approval_state", None)
                      or getattr(gov, "authorization_state", None) or "")
    history = tuple(getattr(gov, "approval_history", None)
                    or getattr(gov, "authorization_history", None) or ())
    authority = (getattr(gov, "approval_authority", None)
                 or getattr(gov, "authorization_authority", None))
    escalation_required = bool(getattr(gov, "escalation_required", False))
    policy_references = tuple(getattr(gov, "policy_references", ()) or ())

    state = _state_value(record)
    # a policy/constraint may not carry an approval projection: derive from lifecycle.
    if not approval_state:
        approval_state = "approved" if state in _LIVE_STATES else (state or "pending")

    decision = history[-1].get("decision", "") if history else ""
    escalated = approval_state == "escalated" or any(
        h.get("decision") == "escalated" for h in history)

    entity_id = getattr(record, _ID_ATTR.get(kind, ""), None) or getattr(record, "entity_id", "")

    return GovernedObservation(
        kind=kind, entity_id=entity_id, approval_state=approval_state, decision=decision,
        authority=authority, history=history, escalation_required=escalation_required,
        escalated=escalated, policy_references=policy_references, state=state,
        lineage_id=getattr(record, "lineage_id", None),
        live=state in _LIVE_STATES)


class GovernanceObservationView:
    """A read-only collection of governed observations + convenience aggregations."""

    def __init__(self, observations: Sequence[GovernedObservation] = ()):
        self._obs: list[GovernedObservation] = list(observations)

    @classmethod
    def from_sources(cls, *, goals: Sequence = (), policies: Sequence = (),
                     constraints: Sequence = (), plans: Sequence = (), tasks: Sequence = (),
                     agents: Sequence = (), executions: Sequence = ()
                     ) -> "GovernanceObservationView":
        obs: list[GovernedObservation] = []
        for kind, records in ((GovernedKind.GOAL, goals), (GovernedKind.POLICY, policies),
                              (GovernedKind.CONSTRAINT, constraints), (GovernedKind.PLAN, plans),
                              (GovernedKind.TASK, tasks), (GovernedKind.AGENT, agents),
                              (GovernedKind.EXECUTION, executions)):
            for rec in records:
                obs.append(observe_record(kind, rec))
        return cls(obs)

    def all(self) -> list[GovernedObservation]:
        return list(self._obs)

    def by_kind(self, kind: str) -> list[GovernedObservation]:
        return [o for o in self._obs if o.kind == kind]

    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted({o.kind for o in self._obs}))

    def parents(self) -> tuple[str, ...]:
        """The lineage nodes of every observed entity (de-duplicated, ordered)."""
        seen: list[str] = []
        for o in self._obs:
            if o.lineage_id and o.lineage_id not in seen:
                seen.append(o.lineage_id)
        return tuple(seen)

    def __len__(self) -> int:
        return len(self._obs)
