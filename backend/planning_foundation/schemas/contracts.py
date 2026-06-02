"""Entity contracts for the planning-foundation domain (V4-P3).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    PLAN_DOMAIN_VERSION, PLAN_IDENTITY_VERSION, PLAN_TAXONOMY_VERSION,
    PLAN_LIFECYCLE_VERSION, PLAN_RELATIONSHIP_VERSION, PLAN_GOVERNANCE_VERSION,
    PLAN_REGISTRY_VERSION, PLAN_AUDIT_VERSION, PLAN_LINEAGE_VERSION,
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
    "PlanIdentity": EntityContract(
        "PlanIdentity", PLAN_IDENTITY_VERSION, ("id", "category", "source_goal_id", "plan_key"),
        ("id matches /^plan\\+[0-9a-f]{16}$/",
         "id derives from category + source_goal_id + plan_key (definition, not state)"),
        "stable across re-declaration", "minting audited via plan creation", "n/a"),
    "PlanRecord": EntityContract(
        "PlanRecord", PLAN_DOMAIN_VERSION,
        ("plan_id", "category", "source_goal_id", "plan_key", "priority", "state", "governance"),
        ("a Plan is an intent structure (how a goal may be achieved) — never execution",
         "category in the closed plan taxonomy; priority in {low,medium,high,critical}",
         "every plan derives from an approved goal; carries no executable action payload"),
        "chained hash(state, previous)", "creation/modification/lifecycle/version audited",
        "parents reach the source goal (and its upstream artifacts, back to the patient)"),
    "PlanMetadata": EntityContract(
        "PlanMetadata", PLAN_DOMAIN_VERSION, ("title", "approach"),
        ("title + approach present (explainable intent)",),
        "part of the plan state signature", "changes audited", "n/a"),
    "PlanCategory": EntityContract(
        "PlanCategory", PLAN_TAXONOMY_VERSION, ("category",),
        ("category in the hierarchical plan taxonomy (strategic apex)",),
        "closed vocabulary; extension is a versioned change", "n/a", "n/a"),
    "PlanPriority": EntityContract(
        "PlanPriority", PLAN_TAXONOMY_VERSION, ("priority",),
        ("priority in {low, medium, high, critical}",), "closed vocabulary", "n/a", "n/a"),
    "PlanVersion": EntityContract(
        "PlanVersion", PLAN_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "PlanLifecycleState": EntityContract(
        "PlanLifecycleState", PLAN_LIFECYCLE_VERSION, ("state",),
        ("state in {proposed,draft,under_review,approved,ready,suspended,completed,archived}",
         "only table-allowed transitions; forbidden transitions blocked",
         "READY requires policy-governed approval"),
        "each transition bumps the plan version", "every transition audited",
        "each transition extends the plan lineage"),
    "PlanDependency": EntityContract(
        "PlanDependency", PLAN_RELATIONSHIP_VERSION,
        ("dependency_id", "source_plan_id", "relation", "target_id", "target_kind"),
        ("relation in {depends_on,supports,blocks,requires,derived_from,influences}",
         "target_kind in {plan,goal,policy,constraint}; depends_on/requires must stay acyclic"),
        "dependencies are versioned", "dependency changes audited",
        "dependency lineage parents the related artifacts' nodes"),
    "PlanRelationship": EntityContract(
        "PlanRelationship", PLAN_RELATIONSHIP_VERSION,
        ("dependency_id", "source_plan_id", "relation", "target_id", "target_kind"),
        ("alias of PlanDependency (a versioned plan relationship edge)",),
        "versioned", "relationship changes audited", "lineage parents the related nodes"),
    "PlanGovernanceRecord": EntityContract(
        "PlanGovernanceRecord", PLAN_GOVERNANCE_VERSION, ("approval_state",),
        ("approval_state in {pending, approved, rejected, escalated}",
         "a plan cannot become READY without governance approval"),
        "part of the plan state signature", "approval events audited",
        "policy + constraint references recorded"),
    "PlanAuditRecord": EntityContract(
        "PlanAuditRecord", PLAN_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "PlanLineageRecord": EntityContract(
        "PlanLineageRecord", PLAN_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach the source goal (to the patient)"),
    "PlanRegistryRecord": EntityContract(
        "PlanRegistryRecord", PLAN_REGISTRY_VERSION,
        ("plan_id", "category", "source_goal_id", "state", "version", "lineage_id"),
        ("no plan exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current plan version", "registry changes audited",
        "lineage_id references the plan lineage node"),
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
    return {"plan_domain_version": PLAN_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
