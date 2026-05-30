"""Entity contracts for the agent-coordination domain (V4-P5).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    AGENT_DOMAIN_VERSION, AGENT_IDENTITY_VERSION, AGENT_TAXONOMY_VERSION,
    AGENT_CAPABILITY_VERSION, AGENT_ASSIGNMENT_VERSION, AGENT_LIFECYCLE_VERSION,
    AGENT_RELATIONSHIP_VERSION, AGENT_GOVERNANCE_VERSION, AGENT_REGISTRY_VERSION,
    AGENT_AUDIT_VERSION, AGENT_LINEAGE_VERSION,
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
    "AgentIdentity": EntityContract(
        "AgentIdentity", AGENT_IDENTITY_VERSION, ("id", "category", "agent_key"),
        ("id matches /^agent\\+[0-9a-f]{16}$/",
         "id derives from category + agent_key (definition, not lifecycle state)"),
        "stable across re-declaration", "minting audited via agent creation", "n/a"),
    "AgentRecord": EntityContract(
        "AgentRecord", AGENT_DOMAIN_VERSION,
        ("agent_id", "category", "agent_key", "priority", "state", "governance"),
        ("an Agent is a governed participant; it describes capability, not authority",
         "category in the closed agent taxonomy; priority in {low,medium,high,critical}",
         "no autonomous/self-modifying/unbounded payload"),
        "chained hash(state, previous)", "creation/modification/lifecycle/version audited",
        "parents reach the governing artifacts it derives from (to the patient)"),
    "AgentMetadata": EntityContract(
        "AgentMetadata", AGENT_DOMAIN_VERSION, ("title", "role"),
        ("title + role present (explainable participant)",),
        "part of the agent state signature", "changes audited", "n/a"),
    "AgentCategory": EntityContract(
        "AgentCategory", AGENT_TAXONOMY_VERSION, ("category",),
        ("category in the hierarchical agent taxonomy (participant apex)",),
        "closed vocabulary; extension is a versioned change", "n/a", "n/a"),
    "AgentCapability": EntityContract(
        "AgentCapability", AGENT_CAPABILITY_VERSION, ("name", "mode", "risk"),
        ("mode in {allowed, restricted, required}; risk in {low,moderate,high,critical}",
         "every capability is policy governed; high/critical risk requires approval",
         "dependencies must be declared on the same agent"),
        "part of the agent state signature", "capability changes audited", "n/a"),
    "AgentAssignment": EntityContract(
        "AgentAssignment", AGENT_ASSIGNMENT_VERSION,
        ("assignment_id", "agent_id", "target_id", "target_kind", "state"),
        ("state in {assigned,pending,blocked,revoked,completed}",
         "an assignment must satisfy the target's capability requirements",
         "an assignment does NOT imply execution"),
        "assignments are versioned", "assignment changes audited",
        "assignment lineage parents the agent node + the work-unit node"),
    "AgentPriority": EntityContract(
        "AgentPriority", AGENT_TAXONOMY_VERSION, ("priority",),
        ("priority in {low, medium, high, critical}",), "closed vocabulary", "n/a", "n/a"),
    "AgentVersion": EntityContract(
        "AgentVersion", AGENT_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "AgentLifecycleState": EntityContract(
        "AgentLifecycleState", AGENT_LIFECYCLE_VERSION, ("state",),
        ("state in {proposed,draft,under_review,approved,available,suspended,retired,archived}",
         "only table-allowed transitions; forbidden transitions blocked",
         "AVAILABLE requires policy-governed approval"),
        "each transition bumps the agent version", "every transition audited",
        "each transition extends the agent lineage"),
    "AgentRelationship": EntityContract(
        "AgentRelationship", AGENT_RELATIONSHIP_VERSION,
        ("relationship_id", "source_agent_id", "relation", "target_id", "target_kind"),
        ("relation in {supports,depends_on,coordinates,derived_from,influences}",
         "target_kind in {agent,goal,policy,plan}"),
        "relationships are versioned", "relationship changes audited",
        "relationship lineage parents the related artifacts' nodes"),
    "AgentGovernanceRecord": EntityContract(
        "AgentGovernanceRecord", AGENT_GOVERNANCE_VERSION, ("approval_state",),
        ("approval_state in {pending, approved, rejected, escalated}",
         "an agent cannot become AVAILABLE without governance approval",
         "capability + assignment approval flags tracked"),
        "part of the agent state signature", "approval events audited",
        "policy + constraint references recorded"),
    "AgentAuditRecord": EntityContract(
        "AgentAuditRecord", AGENT_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "AgentLineageRecord": EntityContract(
        "AgentLineageRecord", AGENT_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach upstream nodes (to the patient)"),
    "AgentRegistryRecord": EntityContract(
        "AgentRegistryRecord", AGENT_REGISTRY_VERSION,
        ("agent_id", "category", "state", "version", "lineage_id"),
        ("no agent exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current agent version", "registry changes audited",
        "lineage_id references the agent lineage node"),
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
    return {"agent_domain_version": AGENT_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
