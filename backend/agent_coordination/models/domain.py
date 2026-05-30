"""Agent domain entities (V4-P5).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. An **Agent** is a
first-class *governed participant* — a description of who/what can perform work, with
declared capabilities and assignments. Agents are **not** autonomous/self-modifying/
unbounded executors. They describe capability; they do not possess autonomous
authority.

Mandated entities: ``AgentIdentity`` (in ``identity``), ``AgentRecord``,
``AgentMetadata``, ``AgentCategory``/``AgentPriority`` (in ``taxonomy``),
``AgentCapability``, ``AgentAssignment``, ``AgentVersion``, ``AgentLifecycleState``
(in ``lifecycle``), ``AgentGovernanceRecord``, ``AgentAuditRecord``,
``AgentLineageRecord``, ``AgentRegistryRecord``, ``AgentRelationship``.

The aggregate ``AgentRecord`` is mutable (its lifecycle state evolves); every other
entity is a frozen, content-addressed value object. All mutation goes through the
service's governed path (validate -> audit -> lineage -> version -> registry).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    AGENT_DOMAIN_VERSION, AGENT_CAPABILITY_VERSION, AGENT_ASSIGNMENT_VERSION,
    AGENT_GOVERNANCE_VERSION, AGENT_RELATIONSHIP_VERSION, AGENT_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)
from ..lifecycle import AgentLifecycleState


# --- metadata -----------------------------------------------------------------
@dataclass(frozen=True)
class AgentMetadata:
    """Descriptive, non-identifying metadata for an agent (describes capability)."""

    title: str = ""
    description: str = ""
    role: str = ""                  # what the participant is (text only)
    contact: str = ""               # how the participant is reached (text only)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description, "role": self.role,
                "contact": self.contact, "tags": list(self.tags)}


# --- capability ---------------------------------------------------------------
@dataclass(frozen=True)
class AgentCapability:
    """A declared, governed capability of an agent.

    ``mode`` is allowed | restricted | required; ``risk`` is the governed risk level
    (low..critical). ``depends_on`` lists capability names this one needs.
    ``constraint_ids`` references policy constraints that govern the capability —
    every capability must be policy governed. ``approved`` records whether governance
    has approved the capability (a high/critical-risk capability is not usable until
    approved). A capability *describes* what an agent may do; it never executes.
    """

    name: str
    mode: str
    risk: str
    description: str = ""
    depends_on: tuple[str, ...] = ()
    constraint_ids: tuple[str, ...] = ()
    approved: bool = False
    capability_version: str = AGENT_CAPABILITY_VERSION

    def state_signature(self) -> str:
        return hash_obj({"name": self.name, "mode": self.mode, "risk": self.risk,
                         "depends_on": list(self.depends_on),
                         "constraint_ids": list(self.constraint_ids), "approved": self.approved})

    def to_dict(self) -> dict:
        return {"name": self.name, "mode": self.mode, "risk": self.risk,
                "description": self.description, "depends_on": list(self.depends_on),
                "constraint_ids": list(self.constraint_ids), "approved": self.approved,
                "capability_version": self.capability_version}


# --- assignment ---------------------------------------------------------------
@dataclass(frozen=True)
class AgentAssignment:
    """A versioned association Agent -> work unit (task | plan | goal | policy).

    An assignment **does not imply execution** — it records that an agent is
    associated with a unit of work in a given ``state`` (assigned | pending | blocked
    | revoked | completed). ``required_capabilities`` are the capabilities the target
    requires; the service validates the agent satisfies them before assigning.
    """

    assignment_id: str
    agent_id: str
    target_id: str
    target_kind: str
    state: str
    required_capabilities: tuple[str, ...] = ()
    lineage_id: Optional[str] = None
    version: str = ""
    assignment_version: str = AGENT_ASSIGNMENT_VERSION

    def state_signature(self) -> str:
        return hash_obj({"agent_id": self.agent_id, "target_id": self.target_id,
                         "target_kind": self.target_kind, "state": self.state,
                         "required_capabilities": list(self.required_capabilities)})

    def to_dict(self) -> dict:
        return {"assignment_id": self.assignment_id, "agent_id": self.agent_id,
                "target_id": self.target_id, "target_kind": self.target_kind,
                "state": self.state, "required_capabilities": list(self.required_capabilities),
                "lineage_id": self.lineage_id, "version": self.version,
                "assignment_version": self.assignment_version,
                "state_signature": self.state_signature()}


# --- constraint reference -----------------------------------------------------
@dataclass(frozen=True)
class AgentConstraintReference:
    """A reference from an agent to a policy/constraint that governs it (V4-P2)."""

    constraint_id: str
    hook: str
    policy_id: Optional[str] = None
    note: str = ""

    def to_dict(self) -> dict:
        return {"constraint_id": self.constraint_id, "hook": self.hook,
                "policy_id": self.policy_id, "note": self.note}


# --- version ------------------------------------------------------------------
@dataclass(frozen=True)
class AgentVersion:
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
class AgentAuditRecord:
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


# --- relationship -------------------------------------------------------------
@dataclass(frozen=True)
class AgentRelationship:
    """A versioned relationship edge Agent -> target (agent | goal | policy | plan)."""

    relationship_id: str
    source_agent_id: str
    relation: str
    target_id: str
    target_kind: str
    version: str = ""
    relationship_version: str = AGENT_RELATIONSHIP_VERSION

    def state_signature(self) -> str:
        return hash_obj({"source": self.source_agent_id, "relation": self.relation,
                         "target": self.target_id, "target_kind": self.target_kind})

    def to_dict(self) -> dict:
        return {"relationship_id": self.relationship_id, "source_agent_id": self.source_agent_id,
                "relation": self.relation, "target_id": self.target_id,
                "target_kind": self.target_kind, "version": self.version,
                "relationship_version": self.relationship_version,
                "state_signature": self.state_signature()}



# --- governance ---------------------------------------------------------------
@dataclass(frozen=True)
class AgentGovernanceRecord:
    """The governance state attached to an agent.

    Tracks approval state/authority/history, capability- and assignment-approval
    flags, escalation requirements, and the policy + constraint references that
    govern the agent's lifecycle. An agent cannot become AVAILABLE without governance
    approval (enforced by the service via the policy engine). Frozen +
    content-addressed; the service replaces it on each change.
    """

    approval_state: str = "pending"          # pending | approved | rejected | escalated
    approval_authority: Optional[str] = None
    approval_history: tuple[dict, ...] = ()
    capability_approved: bool = False
    assignment_approved: bool = False
    escalation_required: bool = False
    policy_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    governance_version: str = AGENT_GOVERNANCE_VERSION

    def with_event(self, *, approval_state: str, authority: Optional[str], hook: str,
                   decision: str, policy_id: Optional[str], created_at: str,
                   capability_approved: Optional[bool] = None,
                   assignment_approved: Optional[bool] = None) -> "AgentGovernanceRecord":
        event = {"hook": hook, "decision": decision, "authority": authority,
                 "policy_id": policy_id, "created_at": created_at}
        refs = self.policy_references + ((policy_id,) if policy_id and
                                         policy_id not in self.policy_references else ())
        return AgentGovernanceRecord(
            approval_state=approval_state, approval_authority=authority or self.approval_authority,
            approval_history=self.approval_history + (event,),
            capability_approved=(self.capability_approved if capability_approved is None
                                 else capability_approved),
            assignment_approved=(self.assignment_approved if assignment_approved is None
                                 else assignment_approved),
            escalation_required=self.escalation_required, policy_references=refs,
            constraint_references=self.constraint_references,
            governance_version=self.governance_version)

    def with_constraint(self, constraint_id: str) -> "AgentGovernanceRecord":
        if constraint_id in self.constraint_references:
            return self
        return AgentGovernanceRecord(
            approval_state=self.approval_state, approval_authority=self.approval_authority,
            approval_history=self.approval_history, capability_approved=self.capability_approved,
            assignment_approved=self.assignment_approved,
            escalation_required=self.escalation_required, policy_references=self.policy_references,
            constraint_references=self.constraint_references + (constraint_id,),
            governance_version=self.governance_version)

    def state_signature(self) -> str:
        return hash_obj({"approval_state": self.approval_state,
                         "approval_authority": self.approval_authority,
                         "approval_history": list(self.approval_history),
                         "capability_approved": self.capability_approved,
                         "assignment_approved": self.assignment_approved,
                         "escalation_required": self.escalation_required,
                         "policy_references": list(self.policy_references),
                         "constraint_references": list(self.constraint_references)})

    def to_dict(self) -> dict:
        return {"approval_state": self.approval_state,
                "approval_authority": self.approval_authority,
                "approval_history": list(self.approval_history),
                "capability_approved": self.capability_approved,
                "assignment_approved": self.assignment_approved,
                "escalation_required": self.escalation_required,
                "policy_references": list(self.policy_references),
                "constraint_references": list(self.constraint_references),
                "governance_version": self.governance_version}


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class AgentLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class AgentRegistryRecord:
    agent_id: str
    category: str
    state: str
    priority: str
    version: str
    approval_state: str
    capabilities: tuple[str, ...]
    assignments: tuple[str, ...]
    policy_references: tuple[str, ...]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    agent_registry_version: str = AGENT_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"agent_id": self.agent_id, "category": self.category,
                         "state": self.state, "priority": self.priority, "version": self.version,
                         "approval_state": self.approval_state, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"agent_id": self.agent_id, "category": self.category, "state": self.state,
                "priority": self.priority, "version": self.version,
                "approval_state": self.approval_state, "capabilities": list(self.capabilities),
                "assignments": list(self.assignments),
                "policy_references": list(self.policy_references), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "agent_registry_version": self.agent_registry_version,
                "content_signature": self.content_signature()}


# --- agent aggregate (mutable; lifecycle evolves) ----------------------------
@dataclass
class AgentRecord:
    """The Agent aggregate — a first-class governed participant (never autonomous)."""

    agent_id: str
    category: str
    agent_key: str
    metadata: AgentMetadata
    priority: str
    state: AgentLifecycleState
    governance: AgentGovernanceRecord
    capabilities: tuple[AgentCapability, ...] = ()
    constraints: tuple[AgentConstraintReference, ...] = ()
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "agent-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = AGENT_DOMAIN_VERSION

    @property
    def constraint_ids(self) -> tuple[str, ...]:
        return tuple(c.constraint_id for c in self.constraints)

    @property
    def capability_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.capabilities)

    def capability(self, name: str) -> Optional[AgentCapability]:
        for c in self.capabilities:
            if c.name == name:
                return c
        return None

    def has_capability(self, name: str) -> bool:
        c = self.capability(name)
        return c is not None and c.mode != "restricted"

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def is_available(self) -> bool:
        return self.state == AgentLifecycleState.AVAILABLE

    def state_signature(self) -> str:
        return hash_obj({
            "agent_id": self.agent_id, "category": self.category, "agent_key": self.agent_key,
            "metadata": self.metadata.to_dict(), "priority": self.priority,
            "state": self.state.value, "governance": self.governance.state_signature(),
            "capabilities": [c.state_signature() for c in self.capabilities],
            "constraints": [c.to_dict() for c in self.constraints],
        })

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id, "category": self.category, "agent_key": self.agent_key,
            "metadata": self.metadata.to_dict(), "priority": self.priority,
            "state": self.state.value, "governance": self.governance.to_dict(),
            "capabilities": [c.to_dict() for c in self.capabilities],
            "constraints": [c.to_dict() for c in self.constraints],
            "constraint_ids": list(self.constraint_ids),
            "capability_names": list(self.capability_names), "version": self.version,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state, "owner": self.owner,
            "created_at": self.created_at, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }
