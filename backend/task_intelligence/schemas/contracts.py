"""Entity contracts for the task-intelligence domain (V4-P4).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    TASK_DOMAIN_VERSION, TASK_IDENTITY_VERSION, TASK_TAXONOMY_VERSION,
    TASK_LIFECYCLE_VERSION, TASK_RELATIONSHIP_VERSION, TASK_GOVERNANCE_VERSION,
    TASK_REGISTRY_VERSION, TASK_AUDIT_VERSION, TASK_LINEAGE_VERSION,
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
    "TaskIdentity": EntityContract(
        "TaskIdentity", TASK_IDENTITY_VERSION, ("id", "category", "source_plan_id", "task_key"),
        ("id matches /^task\\+[0-9a-f]{16}$/",
         "id derives from category + source_plan_id + task_key (definition, not state)"),
        "stable across re-declaration", "minting audited via task creation", "n/a"),
    "TaskRecord": EntityContract(
        "TaskRecord", TASK_DOMAIN_VERSION,
        ("task_id", "category", "source_plan_id", "task_key", "priority", "state", "governance"),
        ("a Task describes work (the atomic unit of future execution) — it never executes",
         "category in the closed task taxonomy; priority in {low,medium,high,critical}",
         "every task derives from a ready plan; carries no executable action payload"),
        "chained hash(state, previous)", "creation/modification/lifecycle/version audited",
        "parents reach the source plan -> goal (and upstream artifacts, back to the patient)"),
    "TaskMetadata": EntityContract(
        "TaskMetadata", TASK_DOMAIN_VERSION, ("title", "work_definition"),
        ("title + work_definition present (explainable; describes work, not execution)",),
        "part of the task state signature", "changes audited", "n/a"),
    "TaskCategory": EntityContract(
        "TaskCategory", TASK_TAXONOMY_VERSION, ("category",),
        ("category in the hierarchical task taxonomy (operational apex)",),
        "closed vocabulary; extension is a versioned change", "n/a", "n/a"),
    "TaskPriority": EntityContract(
        "TaskPriority", TASK_TAXONOMY_VERSION, ("priority",),
        ("priority in {low, medium, high, critical}",), "closed vocabulary", "n/a", "n/a"),
    "TaskVersion": EntityContract(
        "TaskVersion", TASK_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "TaskLifecycleState": EntityContract(
        "TaskLifecycleState", TASK_LIFECYCLE_VERSION, ("state",),
        ("state in {proposed,draft,under_review,approved,ready,blocked,completed,archived}",
         "only table-allowed transitions; forbidden transitions blocked",
         "READY requires policy-governed approval; BLOCKED is an operational dep state"),
        "each transition bumps the task version", "every transition audited",
        "each transition extends the task lineage"),
    "TaskDependency": EntityContract(
        "TaskDependency", TASK_RELATIONSHIP_VERSION,
        ("dependency_id", "source_task_id", "relation", "target_id", "target_kind"),
        ("relation in {depends_on,blocks,supports,requires,derived_from,influences}",
         "target_kind in {task,plan,goal,policy}; depends_on/requires must stay acyclic"),
        "dependencies are versioned", "dependency changes audited",
        "dependency lineage parents the related artifacts' nodes"),
    "TaskRelationship": EntityContract(
        "TaskRelationship", TASK_RELATIONSHIP_VERSION,
        ("dependency_id", "source_task_id", "relation", "target_id", "target_kind"),
        ("alias of TaskDependency (a versioned task relationship edge)",),
        "versioned", "relationship changes audited", "lineage parents the related nodes"),
    "TaskGovernanceRecord": EntityContract(
        "TaskGovernanceRecord", TASK_GOVERNANCE_VERSION, ("approval_state",),
        ("approval_state in {pending, approved, rejected, escalated}",
         "a task cannot become READY without governance approval"),
        "part of the task state signature", "approval events audited",
        "policy + constraint references recorded"),
    "TaskAuditRecord": EntityContract(
        "TaskAuditRecord", TASK_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "TaskLineageRecord": EntityContract(
        "TaskLineageRecord", TASK_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach the source plan (to the patient)"),
    "TaskRegistryRecord": EntityContract(
        "TaskRegistryRecord", TASK_REGISTRY_VERSION,
        ("task_id", "category", "source_plan_id", "state", "version", "lineage_id"),
        ("no task exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current task version", "registry changes audited",
        "lineage_id references the task lineage node"),
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
    return {"task_domain_version": TASK_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
