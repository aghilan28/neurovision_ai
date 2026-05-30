"""Plan domain entities (V4-P3).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. A **Plan** is the
bridge between an approved Goal and Tasks: it defines *how a goal may be achieved*.
A plan is an **intent structure**, never execution, task completion, agent behavior,
or autonomous action.

Mandated entities: ``PlanIdentity`` (in ``identity``), ``PlanRecord``,
``PlanMetadata``, ``PlanCategory``/``PlanPriority`` (in ``taxonomy``),
``PlanVersion``, ``PlanLifecycleState`` (in ``lifecycle``), ``PlanDependency``,
``PlanGovernanceRecord``, ``PlanAuditRecord``, ``PlanLineageRecord``,
``PlanRegistryRecord``, ``PlanRelationship``.

The aggregate ``PlanRecord`` is mutable (its lifecycle state evolves); every other
entity is a frozen, content-addressed value object. All mutation goes through the
service's governed path (validate -> audit -> lineage -> version -> registry).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    PLAN_DOMAIN_VERSION, PLAN_GOVERNANCE_VERSION, PLAN_RELATIONSHIP_VERSION,
    PLAN_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)
from ..lifecycle import PlanLifecycleState


# --- metadata -----------------------------------------------------------------
@dataclass(frozen=True)
class PlanMetadata:
    """Descriptive, non-identifying metadata for a plan (intent, never execution)."""

    title: str = ""
    description: str = ""
    approach: str = ""              # how the goal may be achieved (text only)
    expected_outcome: str = ""
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description,
                "approach": self.approach, "expected_outcome": self.expected_outcome,
                "tags": list(self.tags)}


# --- constraint reference -----------------------------------------------------
@dataclass(frozen=True)
class PlanConstraintReference:
    """A reference from a plan to a policy/constraint that governs it (V4-P2).

    The planning subsystem does not own constraint logic; it only *references* a
    policy constraint id. ``hook`` names the lifecycle integration point
    (plan_approval | plan_readiness | ...).
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
class PlanVersion:
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
class PlanAuditRecord:
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


# --- dependency ---------------------------------------------------------------
@dataclass(frozen=True)
class PlanDependency:
    """A versioned dependency edge Plan -> target (plan | goal | policy | constraint)."""

    dependency_id: str
    source_plan_id: str
    relation: str
    target_id: str
    target_kind: str
    version: str = ""
    relationship_version: str = PLAN_RELATIONSHIP_VERSION

    def state_signature(self) -> str:
        return hash_obj({"source": self.source_plan_id, "relation": self.relation,
                         "target": self.target_id, "target_kind": self.target_kind})

    def to_dict(self) -> dict:
        return {"dependency_id": self.dependency_id, "source_plan_id": self.source_plan_id,
                "relation": self.relation, "target_id": self.target_id,
                "target_kind": self.target_kind, "version": self.version,
                "relationship_version": self.relationship_version,
                "state_signature": self.state_signature()}


# PlanRelationship is the public alias for a plan dependency edge (mandated entity).
PlanRelationship = PlanDependency



# --- governance ---------------------------------------------------------------
@dataclass(frozen=True)
class PlanGovernanceRecord:
    """The governance state attached to a plan.

    Tracks approval state/authority/history, escalation requirements, and the policy
    + constraint references that govern the plan's lifecycle. A plan cannot become
    READY without governance approval (enforced by the service via the policy
    engine). Frozen + content-addressed; the service replaces it on each change.
    """

    approval_state: str = "pending"          # pending | approved | rejected | escalated
    approval_authority: Optional[str] = None
    approval_history: tuple[dict, ...] = ()
    escalation_required: bool = False
    policy_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    governance_version: str = PLAN_GOVERNANCE_VERSION

    def with_event(self, *, approval_state: str, authority: Optional[str], hook: str,
                   decision: str, policy_id: Optional[str], created_at: str
                   ) -> "PlanGovernanceRecord":
        event = {"hook": hook, "decision": decision, "authority": authority,
                 "policy_id": policy_id, "created_at": created_at}
        refs = self.policy_references + ((policy_id,) if policy_id and
                                         policy_id not in self.policy_references else ())
        return PlanGovernanceRecord(
            approval_state=approval_state, approval_authority=authority or self.approval_authority,
            approval_history=self.approval_history + (event,),
            escalation_required=self.escalation_required, policy_references=refs,
            constraint_references=self.constraint_references,
            governance_version=self.governance_version)

    def with_constraint(self, constraint_id: str) -> "PlanGovernanceRecord":
        if constraint_id in self.constraint_references:
            return self
        return PlanGovernanceRecord(
            approval_state=self.approval_state, approval_authority=self.approval_authority,
            approval_history=self.approval_history, escalation_required=self.escalation_required,
            policy_references=self.policy_references,
            constraint_references=self.constraint_references + (constraint_id,),
            governance_version=self.governance_version)

    def state_signature(self) -> str:
        return hash_obj({"approval_state": self.approval_state,
                         "approval_authority": self.approval_authority,
                         "approval_history": list(self.approval_history),
                         "escalation_required": self.escalation_required,
                         "policy_references": list(self.policy_references),
                         "constraint_references": list(self.constraint_references)})

    def to_dict(self) -> dict:
        return {"approval_state": self.approval_state,
                "approval_authority": self.approval_authority,
                "approval_history": list(self.approval_history),
                "escalation_required": self.escalation_required,
                "policy_references": list(self.policy_references),
                "constraint_references": list(self.constraint_references),
                "governance_version": self.governance_version}


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class PlanLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class PlanRegistryRecord:
    plan_id: str
    category: str
    source_goal_id: str
    state: str
    priority: str
    version: str
    approval_state: str
    dependencies: tuple[str, ...]
    goal_references: tuple[str, ...]
    policy_references: tuple[str, ...]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    plan_registry_version: str = PLAN_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"plan_id": self.plan_id, "category": self.category,
                         "source_goal_id": self.source_goal_id, "state": self.state,
                         "priority": self.priority, "version": self.version,
                         "approval_state": self.approval_state, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"plan_id": self.plan_id, "category": self.category,
                "source_goal_id": self.source_goal_id, "state": self.state,
                "priority": self.priority, "version": self.version,
                "approval_state": self.approval_state, "dependencies": list(self.dependencies),
                "goal_references": list(self.goal_references),
                "policy_references": list(self.policy_references), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "plan_registry_version": self.plan_registry_version,
                "content_signature": self.content_signature()}


# --- plan aggregate (mutable; lifecycle evolves) -----------------------------
@dataclass
class PlanRecord:
    """The Plan aggregate — a first-class intent structure (never execution)."""

    plan_id: str
    category: str
    source_goal_id: str
    plan_key: str
    metadata: PlanMetadata
    priority: str
    state: PlanLifecycleState
    governance: PlanGovernanceRecord
    constraints: tuple[PlanConstraintReference, ...] = ()
    dependencies: tuple[str, ...] = ()        # plan_ids this plan depends on
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "plan-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = PLAN_DOMAIN_VERSION

    @property
    def constraint_ids(self) -> tuple[str, ...]:
        return tuple(c.constraint_id for c in self.constraints)

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def is_ready(self) -> bool:
        return self.state == PlanLifecycleState.READY

    def state_signature(self) -> str:
        return hash_obj({
            "plan_id": self.plan_id, "category": self.category,
            "source_goal_id": self.source_goal_id, "plan_key": self.plan_key,
            "metadata": self.metadata.to_dict(), "priority": self.priority,
            "state": self.state.value, "governance": self.governance.state_signature(),
            "constraints": [c.to_dict() for c in self.constraints],
            "dependencies": list(self.dependencies),
        })

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id, "category": self.category,
            "source_goal_id": self.source_goal_id, "plan_key": self.plan_key,
            "metadata": self.metadata.to_dict(), "priority": self.priority,
            "state": self.state.value, "governance": self.governance.to_dict(),
            "constraints": [c.to_dict() for c in self.constraints],
            "dependencies": list(self.dependencies), "constraint_ids": list(self.constraint_ids),
            "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "owner": self.owner, "created_at": self.created_at,
            "domain_version": self.domain_version, "state_signature": self.state_signature(),
        }
