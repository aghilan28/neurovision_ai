"""Goal domain entities (V4-P1).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. A **Goal** is
*intent* — a desired outcome — never a recommendation, task, plan, or execution.
Goals never directly perform actions.

Mandated entities: ``GoalIdentity`` (in ``identity``), ``GoalRecord``,
``GoalMetadata``, ``GoalCategory``/``GoalPriority`` (in ``taxonomy``),
``GoalVersion``, ``GoalLifecycleState`` (in ``lifecycle``),
``GoalConstraintReference``, ``GoalAuditRecord``, ``GoalLineageRecord``,
``GoalRegistryRecord``, ``GoalRelationship``.

The aggregate ``Goal`` is mutable (its lifecycle state evolves); every other entity
is a frozen, content-addressed value object. All mutation goes through the service's
governed path (validate -> audit -> lineage -> version -> registry).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    GOAL_DOMAIN_VERSION, GOAL_GOVERNANCE_VERSION, GOAL_RELATIONSHIP_VERSION,
    GOAL_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)
from ..lifecycle import GoalLifecycleState


# --- metadata -----------------------------------------------------------------
@dataclass(frozen=True)
class GoalMetadata:
    """Descriptive, non-identifying metadata for a goal (intent, never execution)."""

    title: str = ""
    description: str = ""
    desired_outcome: str = ""
    measure: str = ""               # how the outcome would be observed (text only)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description,
                "desired_outcome": self.desired_outcome, "measure": self.measure,
                "tags": list(self.tags)}


# --- constraint reference -----------------------------------------------------
@dataclass(frozen=True)
class GoalConstraintReference:
    """A reference from a goal to a policy/constraint that governs it (V4-P2).

    The goal subsystem does not own constraint logic; it only *references* a policy
    constraint id (resolved by the policy engine). ``hook`` names the lifecycle
    integration point (goal_approval | goal_activation | ...).
    """

    constraint_id: str
    hook: str
    policy_id: Optional[str] = None
    note: str = ""

    def to_dict(self) -> dict:
        return {"constraint_id": self.constraint_id, "hook": self.hook,
                "policy_id": self.policy_id, "note": self.note}


# --- version ------------------------------------------------------------------
@dataclass(frozen=True)
class GoalVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


# --- audit record -------------------------------------------------------------
@dataclass(frozen=True)
class GoalAuditRecord:
    """An immutable audit event; field-compatible with the shared ImmutableAuditLog."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}



# --- governance ---------------------------------------------------------------
@dataclass(frozen=True)
class GoalGovernance:
    """The governance state attached to a goal.

    Tracks approval state/authority/history, the review + escalation requirements,
    and the policy references that govern the goal's lifecycle. A goal cannot become
    ACTIVE without governance approval (enforced by the service via the policy
    engine). Frozen + content-addressed; the service replaces it on each change.
    """

    approval_state: str = "pending"          # pending | approved | rejected | escalated
    approval_authority: Optional[str] = None
    approval_history: tuple[dict, ...] = ()
    review_required: bool = True
    escalation_required: bool = False
    policy_references: tuple[str, ...] = ()
    governance_version: str = GOAL_GOVERNANCE_VERSION

    def with_event(self, *, approval_state: str, authority: Optional[str], hook: str,
                   decision: str, policy_id: Optional[str], created_at: str) -> "GoalGovernance":
        event = {"hook": hook, "decision": decision, "authority": authority,
                 "policy_id": policy_id, "created_at": created_at}
        refs = self.policy_references + ((policy_id,) if policy_id and
                                         policy_id not in self.policy_references else ())
        return GoalGovernance(
            approval_state=approval_state, approval_authority=authority or self.approval_authority,
            approval_history=self.approval_history + (event,),
            review_required=self.review_required, escalation_required=self.escalation_required,
            policy_references=refs, governance_version=self.governance_version)

    def state_signature(self) -> str:
        return hash_obj({"approval_state": self.approval_state,
                         "approval_authority": self.approval_authority,
                         "approval_history": list(self.approval_history),
                         "review_required": self.review_required,
                         "escalation_required": self.escalation_required,
                         "policy_references": list(self.policy_references)})

    def to_dict(self) -> dict:
        return {"approval_state": self.approval_state,
                "approval_authority": self.approval_authority,
                "approval_history": list(self.approval_history),
                "review_required": self.review_required,
                "escalation_required": self.escalation_required,
                "policy_references": list(self.policy_references),
                "governance_version": self.governance_version}


# --- relationship -------------------------------------------------------------
@dataclass(frozen=True)
class GoalRelationship:
    """A versioned relationship from a goal to another artifact.

    ``source_goal_id`` -> (``relation``) -> ``target_id`` of ``target_kind``
    (goal | workflow | analytics | recommendation | risk | governance).
    """

    relationship_id: str
    source_goal_id: str
    relation: str
    target_id: str
    target_kind: str
    version: str = ""
    relationship_version: str = GOAL_RELATIONSHIP_VERSION

    def state_signature(self) -> str:
        return hash_obj({"source": self.source_goal_id, "relation": self.relation,
                         "target": self.target_id, "target_kind": self.target_kind})

    def to_dict(self) -> dict:
        return {"relationship_id": self.relationship_id, "source_goal_id": self.source_goal_id,
                "relation": self.relation, "target_id": self.target_id,
                "target_kind": self.target_kind, "version": self.version,
                "relationship_version": self.relationship_version,
                "state_signature": self.state_signature()}


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class GoalLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class GoalRegistryRecord:
    goal_id: str
    category: str
    state: str
    priority: str
    version: str
    approval_state: str
    dependencies: tuple[str, ...]
    constraint_ids: tuple[str, ...]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    goal_registry_version: str = GOAL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"goal_id": self.goal_id, "category": self.category, "state": self.state,
                         "priority": self.priority, "version": self.version,
                         "approval_state": self.approval_state, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"goal_id": self.goal_id, "category": self.category, "state": self.state,
                "priority": self.priority, "version": self.version,
                "approval_state": self.approval_state, "dependencies": list(self.dependencies),
                "constraint_ids": list(self.constraint_ids), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "goal_registry_version": self.goal_registry_version,
                "content_signature": self.content_signature()}


# --- goal aggregate (mutable; lifecycle evolves) -----------------------------
@dataclass
class GoalRecord:
    """The Goal aggregate — a first-class statement of intent (never execution)."""

    goal_id: str
    category: str
    definition_key: str
    metadata: GoalMetadata
    priority: str
    state: GoalLifecycleState
    governance: GoalGovernance
    constraints: tuple[GoalConstraintReference, ...] = ()
    dependencies: tuple[str, ...] = ()        # goal_ids this goal depends on
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "goal-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = GOAL_DOMAIN_VERSION

    @property
    def constraint_ids(self) -> tuple[str, ...]:
        return tuple(c.constraint_id for c in self.constraints)

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def is_active(self) -> bool:
        return self.state == GoalLifecycleState.ACTIVE

    def state_signature(self) -> str:
        return hash_obj({
            "goal_id": self.goal_id, "category": self.category,
            "definition_key": self.definition_key, "metadata": self.metadata.to_dict(),
            "priority": self.priority, "state": self.state.value,
            "governance": self.governance.state_signature(),
            "constraints": [c.to_dict() for c in self.constraints],
            "dependencies": list(self.dependencies),
        })

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id, "category": self.category,
            "definition_key": self.definition_key, "metadata": self.metadata.to_dict(),
            "priority": self.priority, "state": self.state.value,
            "governance": self.governance.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
            "dependencies": list(self.dependencies), "constraint_ids": list(self.constraint_ids),
            "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "owner": self.owner, "created_at": self.created_at,
            "domain_version": self.domain_version, "state_signature": self.state_signature(),
        }
