"""Entity contracts for the goal-intelligence domain (V4-P1).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    GOAL_DOMAIN_VERSION, GOAL_IDENTITY_VERSION, GOAL_TAXONOMY_VERSION,
    GOAL_LIFECYCLE_VERSION, GOAL_RELATIONSHIP_VERSION, GOAL_GOVERNANCE_VERSION,
    GOAL_REGISTRY_VERSION, GOAL_AUDIT_VERSION, GOAL_LINEAGE_VERSION,
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
    "GoalIdentity": EntityContract(
        "GoalIdentity", GOAL_IDENTITY_VERSION, ("id", "category", "definition_key"),
        ("id matches /^goal\\+[0-9a-f]{16}$/",
         "id derives from category + definition_key (definition, not lifecycle state)"),
        "stable across re-declaration", "minting audited via goal creation", "n/a"),
    "GoalRecord": EntityContract(
        "GoalRecord", GOAL_DOMAIN_VERSION,
        ("goal_id", "category", "definition_key", "priority", "state", "governance"),
        ("a Goal is intent (a desired outcome) — never a recommendation/task/plan/execution",
         "category in the closed goal taxonomy; priority in {low,medium,high,critical}",
         "carries no executable action payload"),
        "chained hash(state, previous)", "creation/modification/lifecycle/version audited",
        "parents reach the upstream artifacts the intent derives from (back to the patient)"),
    "GoalMetadata": EntityContract(
        "GoalMetadata", GOAL_DOMAIN_VERSION, ("title", "desired_outcome"),
        ("title + desired_outcome present (explainable intent)",),
        "part of the goal state signature", "changes audited", "n/a"),
    "GoalCategory": EntityContract(
        "GoalCategory", GOAL_TAXONOMY_VERSION, ("category",),
        ("category in the hierarchical goal taxonomy (strategic apex)",),
        "closed vocabulary; extension is a versioned change", "n/a", "n/a"),
    "GoalPriority": EntityContract(
        "GoalPriority", GOAL_TAXONOMY_VERSION, ("priority",),
        ("priority in {low, medium, high, critical}",),
        "closed vocabulary", "n/a", "n/a"),
    "GoalVersion": EntityContract(
        "GoalVersion", GOAL_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "GoalLifecycleState": EntityContract(
        "GoalLifecycleState", GOAL_LIFECYCLE_VERSION, ("state",),
        ("state in {proposed,draft,under_review,approved,active,suspended,completed,archived}",
         "only table-allowed transitions; forbidden transitions blocked",
         "ACTIVE requires policy-governed approval"),
        "each transition bumps the goal version", "every transition audited",
        "each transition extends the goal lineage"),
    "GoalConstraintReference": EntityContract(
        "GoalConstraintReference", GOAL_DOMAIN_VERSION, ("constraint_id", "hook"),
        ("references a policy-engine constraint id (goal does not own constraint logic)",),
        "part of the goal state signature", "attachment audited", "n/a"),
    "GoalAuditRecord": EntityContract(
        "GoalAuditRecord", GOAL_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "GoalLineageRecord": EntityContract(
        "GoalLineageRecord", GOAL_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach upstream nodes (to the patient)"),
    "GoalRegistryRecord": EntityContract(
        "GoalRegistryRecord", GOAL_REGISTRY_VERSION,
        ("goal_id", "category", "state", "version", "lineage_id"),
        ("no goal exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current goal version", "registry changes audited",
        "lineage_id references the goal lineage node"),
    "GoalRelationship": EntityContract(
        "GoalRelationship", GOAL_RELATIONSHIP_VERSION,
        ("relationship_id", "source_goal_id", "relation", "target_id", "target_kind"),
        ("relation in {depends_on,supports,conflicts_with,derived_from,influences,blocked_by}",
         "target_kind in {goal,workflow,analytics,recommendation,risk,governance}"),
        "relationships are versioned", "relationship changes audited",
        "relationship lineage parents the related artifacts' nodes"),
    "GoalGovernance": EntityContract(
        "GoalGovernance", GOAL_GOVERNANCE_VERSION, ("approval_state",),
        ("approval_state in {pending, approved, rejected, escalated}",
         "a goal cannot become ACTIVE without governance approval"),
        "part of the goal state signature", "approval events audited",
        "policy references recorded"),
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
    return {"goal_domain_version": GOAL_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
