"""Execution domain entities (V4-P6).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. An **Execution**
represents the *governed progression of approved work*. It is **not** autonomous
action, self-directed operation, or agent freedom: it does not bypass policy or
governance, coordinates already-approved artifacts deterministically, and never
performs autonomous planning.

Mandated entities: ``ExecutionIdentity`` (in ``identity``), ``ExecutionRecord``,
``ExecutionMetadata``, ``ExecutionContext``, ``ExecutionAssignment``,
``ExecutionStatus``, ``ExecutionVersion``, ``ExecutionLifecycleState`` (in
``lifecycle``), ``ExecutionGovernanceRecord``, ``ExecutionAuditRecord``,
``ExecutionLineageRecord``, ``ExecutionRegistryRecord``, ``ExecutionRelationship``.

The aggregate ``ExecutionRecord`` is mutable (its lifecycle state evolves); every
other entity is a frozen, content-addressed value object. All mutation goes through
the service's governed path (validate -> audit -> lineage -> version -> registry).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    EXECUTION_DOMAIN_VERSION, EXECUTION_CONTEXT_VERSION, EXECUTION_STATUS_VERSION,
    EXECUTION_GOVERNANCE_VERSION, EXECUTION_RELATIONSHIP_VERSION, EXECUTION_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)
from ..lifecycle import ExecutionLifecycleState


# --- metadata -----------------------------------------------------------------
@dataclass(frozen=True)
class ExecutionMetadata:
    """Descriptive, non-identifying metadata for an execution (governed progression)."""

    title: str = ""
    description: str = ""
    objective: str = ""             # what approved work this execution progresses (text)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"title": self.title, "description": self.description,
                "objective": self.objective, "tags": list(self.tags)}


# --- coordination context -----------------------------------------------------
@dataclass(frozen=True)
class ExecutionContext:
    """The deterministic coordination context an execution references.

    It binds the execution to the already-approved upstream artifacts it coordinates
    — goal, plan, task, agent, assignment, plus any policy/constraint references.
    Coordination references existing approved artifacts; it never creates or plans
    new ones (no autonomous planning).
    """

    goal_id: str = ""
    plan_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    assignment_id: str = ""
    policy_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    context_version: str = EXECUTION_CONTEXT_VERSION

    def state_signature(self) -> str:
        return hash_obj({"goal_id": self.goal_id, "plan_id": self.plan_id,
                         "task_id": self.task_id, "agent_id": self.agent_id,
                         "assignment_id": self.assignment_id,
                         "policy_references": list(self.policy_references),
                         "constraint_references": list(self.constraint_references)})

    def to_dict(self) -> dict:
        return {"goal_id": self.goal_id, "plan_id": self.plan_id, "task_id": self.task_id,
                "agent_id": self.agent_id, "assignment_id": self.assignment_id,
                "policy_references": list(self.policy_references),
                "constraint_references": list(self.constraint_references),
                "context_version": self.context_version}


# --- status (monitoring observation; never modifies execution) ---------------
@dataclass(frozen=True)
class ExecutionStatus:
    """An observed status snapshot of an execution (read-only monitoring projection).

    ``progress`` is a deterministic [0,1] index derived from the lifecycle state (not
    from wall-clock). ``blocking_conditions`` / ``risks`` / ``escalations`` record
    observed conditions. Monitoring *observes* execution — it never modifies it.
    """

    state: str
    progress: float
    blocking_conditions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    escalations: tuple[str, ...] = ()
    outcome: str = ""
    status_version: str = EXECUTION_STATUS_VERSION

    def to_dict(self) -> dict:
        return {"state": self.state, "progress": self.progress,
                "blocking_conditions": list(self.blocking_conditions),
                "risks": list(self.risks), "escalations": list(self.escalations),
                "outcome": self.outcome, "status_version": self.status_version}


# --- assignment reference -----------------------------------------------------
@dataclass(frozen=True)
class ExecutionAssignment:
    """A reference to the approved agent assignment an execution progresses.

    Every execution must reference an approved assignment (Agent <-> Execution
    integration). ``assignment_state`` mirrors the agent-assignment state at
    reference time. An execution never *creates* assignments; it references them.
    """

    assignment_id: str
    agent_id: str
    task_id: str
    assignment_state: str

    def to_dict(self) -> dict:
        return {"assignment_id": self.assignment_id, "agent_id": self.agent_id,
                "task_id": self.task_id, "assignment_state": self.assignment_state}


# --- version ------------------------------------------------------------------
@dataclass(frozen=True)
class ExecutionVersion:
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
class ExecutionAuditRecord:
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
class ExecutionRelationship:
    """A versioned relationship edge Execution -> target (execution | task | agent | ...)."""

    relationship_id: str
    source_execution_id: str
    relation: str
    target_id: str
    target_kind: str
    version: str = ""
    relationship_version: str = EXECUTION_RELATIONSHIP_VERSION

    def state_signature(self) -> str:
        return hash_obj({"source": self.source_execution_id, "relation": self.relation,
                         "target": self.target_id, "target_kind": self.target_kind})

    def to_dict(self) -> dict:
        return {"relationship_id": self.relationship_id,
                "source_execution_id": self.source_execution_id, "relation": self.relation,
                "target_id": self.target_id, "target_kind": self.target_kind,
                "version": self.version, "relationship_version": self.relationship_version,
                "state_signature": self.state_signature()}



# --- governance ---------------------------------------------------------------
@dataclass(frozen=True)
class ExecutionGovernanceRecord:
    """The governance + authorization state attached to an execution.

    Tracks authorization state/authority/history, escalation requirements, and the
    policy + constraint references that govern the execution. An execution cannot
    become ACTIVE without authorization (and governance approval) — enforced by the
    service via the policy engine. Frozen + content-addressed.
    """

    authorization_state: str = "pending"     # pending | authorized | denied | escalated
    authorization_authority: Optional[str] = None
    authorization_history: tuple[dict, ...] = ()
    escalation_required: bool = False
    policy_references: tuple[str, ...] = ()
    constraint_references: tuple[str, ...] = ()
    governance_version: str = EXECUTION_GOVERNANCE_VERSION

    def with_event(self, *, authorization_state: str, authority: Optional[str], hook: str,
                   decision: str, policy_id: Optional[str], created_at: str
                   ) -> "ExecutionGovernanceRecord":
        event = {"hook": hook, "decision": decision, "authority": authority,
                 "policy_id": policy_id, "created_at": created_at}
        refs = self.policy_references + ((policy_id,) if policy_id and
                                         policy_id not in self.policy_references else ())
        return ExecutionGovernanceRecord(
            authorization_state=authorization_state,
            authorization_authority=authority or self.authorization_authority,
            authorization_history=self.authorization_history + (event,),
            escalation_required=self.escalation_required, policy_references=refs,
            constraint_references=self.constraint_references,
            governance_version=self.governance_version)

    def with_constraint(self, constraint_id: str) -> "ExecutionGovernanceRecord":
        if constraint_id in self.constraint_references:
            return self
        return ExecutionGovernanceRecord(
            authorization_state=self.authorization_state,
            authorization_authority=self.authorization_authority,
            authorization_history=self.authorization_history,
            escalation_required=self.escalation_required, policy_references=self.policy_references,
            constraint_references=self.constraint_references + (constraint_id,),
            governance_version=self.governance_version)

    def state_signature(self) -> str:
        return hash_obj({"authorization_state": self.authorization_state,
                         "authorization_authority": self.authorization_authority,
                         "authorization_history": list(self.authorization_history),
                         "escalation_required": self.escalation_required,
                         "policy_references": list(self.policy_references),
                         "constraint_references": list(self.constraint_references)})

    def to_dict(self) -> dict:
        return {"authorization_state": self.authorization_state,
                "authorization_authority": self.authorization_authority,
                "authorization_history": list(self.authorization_history),
                "escalation_required": self.escalation_required,
                "policy_references": list(self.policy_references),
                "constraint_references": list(self.constraint_references),
                "governance_version": self.governance_version}


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class ExecutionLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class ExecutionRegistryRecord:
    execution_id: str
    source_task_id: str
    assignment_id: str
    state: str
    version: str
    authorization_state: str
    agent_references: tuple[str, ...]
    task_references: tuple[str, ...]
    policy_references: tuple[str, ...]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    execution_registry_version: str = EXECUTION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"execution_id": self.execution_id, "source_task_id": self.source_task_id,
                         "assignment_id": self.assignment_id, "state": self.state,
                         "version": self.version, "authorization_state": self.authorization_state,
                         "lineage_id": self.lineage_id, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"execution_id": self.execution_id, "source_task_id": self.source_task_id,
                "assignment_id": self.assignment_id, "state": self.state, "version": self.version,
                "authorization_state": self.authorization_state,
                "agent_references": list(self.agent_references),
                "task_references": list(self.task_references),
                "policy_references": list(self.policy_references), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "execution_registry_version": self.execution_registry_version,
                "content_signature": self.content_signature()}


# --- execution aggregate (mutable; lifecycle evolves) ------------------------
@dataclass
class ExecutionRecord:
    """The Execution aggregate — the governed progression of approved work."""

    execution_id: str
    execution_key: str
    metadata: ExecutionMetadata
    context: ExecutionContext
    assignment: ExecutionAssignment
    state: ExecutionLifecycleState
    governance: ExecutionGovernanceRecord
    status: ExecutionStatus = field(default=None)  # type: ignore[assignment]
    constraints: tuple[str, ...] = ()              # constraint ids referenced
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "execution-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = EXECUTION_DOMAIN_VERSION

    @property
    def source_task_id(self) -> str:
        return self.context.task_id

    @property
    def assignment_id(self) -> str:
        return self.assignment.assignment_id

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def is_active(self) -> bool:
        return self.state == ExecutionLifecycleState.ACTIVE

    def state_signature(self) -> str:
        return hash_obj({
            "execution_id": self.execution_id, "execution_key": self.execution_key,
            "metadata": self.metadata.to_dict(), "context": self.context.state_signature(),
            "assignment": self.assignment.to_dict(), "state": self.state.value,
            "governance": self.governance.state_signature(),
            "status": self.status.to_dict() if self.status else None,
            "constraints": list(self.constraints),
        })

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id, "execution_key": self.execution_key,
            "metadata": self.metadata.to_dict(), "context": self.context.to_dict(),
            "assignment": self.assignment.to_dict(), "state": self.state.value,
            "governance": self.governance.to_dict(),
            "status": self.status.to_dict() if self.status else None,
            "constraints": list(self.constraints), "source_task_id": self.source_task_id,
            "assignment_id": self.assignment_id, "version": self.version,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state, "owner": self.owner,
            "created_at": self.created_at, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }
