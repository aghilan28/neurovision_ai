"""Entity contracts for the execution-orchestration domain (V4-P6).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    EXECUTION_DOMAIN_VERSION, EXECUTION_IDENTITY_VERSION, EXECUTION_LIFECYCLE_VERSION,
    EXECUTION_CONTEXT_VERSION, EXECUTION_STATUS_VERSION, EXECUTION_RELATIONSHIP_VERSION,
    EXECUTION_GOVERNANCE_VERSION, EXECUTION_REGISTRY_VERSION, EXECUTION_AUDIT_VERSION,
    EXECUTION_LINEAGE_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    version_rule: str
    audit_rule: str
    lineage_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "version_rule": self.version_rule, "audit_rule": self.audit_rule,
                "lineage_rule": self.lineage_rule}



ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "ExecutionIdentity": EntityContract(
        "ExecutionIdentity", EXECUTION_IDENTITY_VERSION,
        ("id", "source_task_id", "assignment_id", "execution_key"),
        ("id matches /^execution\\+[0-9a-f]{16}$/",
         "id derives from source_task_id + assignment_id + execution_key (not state)"),
        "stable across re-declaration", "minting audited via execution creation", "n/a"),
    "ExecutionRecord": EntityContract(
        "ExecutionRecord", EXECUTION_DOMAIN_VERSION,
        ("execution_id", "execution_key", "context", "assignment", "state", "governance"),
        ("an Execution is the governed progression of approved work — never autonomous",
         "references an approved agent assignment; does not bypass policy/governance",
         "carries no autonomous/self-directed payload; no autonomous planning"),
        "chained hash(state, previous)", "creation/authorization/lifecycle/version audited",
        "parents reach the assignment -> agent/task -> ... -> patient"),
    "ExecutionMetadata": EntityContract(
        "ExecutionMetadata", EXECUTION_DOMAIN_VERSION, ("title", "objective"),
        ("title + objective present (explainable progression)",),
        "part of the execution state signature", "changes audited", "n/a"),
    "ExecutionContext": EntityContract(
        "ExecutionContext", EXECUTION_CONTEXT_VERSION, ("task_id", "agent_id", "assignment_id"),
        ("binds approved goal/plan/task/agent/assignment; references, never creates",),
        "part of the execution state signature", "n/a", "coordinates approved artifacts"),
    "ExecutionAssignment": EntityContract(
        "ExecutionAssignment", EXECUTION_DOMAIN_VERSION,
        ("assignment_id", "agent_id", "task_id", "assignment_state"),
        ("references an approved agent assignment (Agent <-> Execution integration)",
         "the execution never creates assignments; it references them"),
        "part of the execution state signature", "n/a", "n/a"),
    "ExecutionStatus": EntityContract(
        "ExecutionStatus", EXECUTION_STATUS_VERSION, ("state", "progress"),
        ("progress is a deterministic [0,1] index from the lifecycle state (not wall-clock)",
         "monitoring observes; it never modifies the execution"),
        "a read-only projection", "n/a", "n/a"),
    "ExecutionVersion": EntityContract(
        "ExecutionVersion", EXECUTION_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "ExecutionLifecycleState": EntityContract(
        "ExecutionLifecycleState", EXECUTION_LIFECYCLE_VERSION, ("state",),
        ("state in {proposed,queued,authorized,active,paused,blocked,completed,terminated,archived}",
         "only table-allowed transitions; forbidden transitions blocked",
         "ACTIVE requires policy-governed authorization"),
        "each transition bumps the execution version", "every transition audited",
        "each transition extends the execution lineage"),
    "ExecutionRelationship": EntityContract(
        "ExecutionRelationship", EXECUTION_RELATIONSHIP_VERSION,
        ("relationship_id", "source_execution_id", "relation", "target_id", "target_kind"),
        ("a versioned execution relationship edge",),
        "relationships are versioned", "relationship changes audited",
        "relationship lineage parents the related artifacts' nodes"),
    "ExecutionGovernanceRecord": EntityContract(
        "ExecutionGovernanceRecord", EXECUTION_GOVERNANCE_VERSION, ("authorization_state",),
        ("authorization_state in {pending, authorized, denied, escalated}",
         "an execution cannot become ACTIVE without authorization"),
        "part of the execution state signature", "authorization events audited",
        "policy + constraint references recorded"),
    "ExecutionAuditRecord": EntityContract(
        "ExecutionAuditRecord", EXECUTION_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "ExecutionLineageRecord": EntityContract(
        "ExecutionLineageRecord", EXECUTION_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach the assignment node (to the patient)"),
    "ExecutionRegistryRecord": EntityContract(
        "ExecutionRegistryRecord", EXECUTION_REGISTRY_VERSION,
        ("execution_id", "source_task_id", "assignment_id", "state", "version", "lineage_id"),
        ("no execution exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current execution version", "registry changes audited",
        "lineage_id references the execution lineage node"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


def all_contracts() -> dict:
    return {"execution_domain_version": EXECUTION_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
