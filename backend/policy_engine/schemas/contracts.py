"""Entity contracts for the policy-engine domain (V4-P2)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    POLICY_DOMAIN_VERSION, POLICY_IDENTITY_VERSION, POLICY_TAXONOMY_VERSION,
    POLICY_RULE_VERSION, CONSTRAINT_VERSION, POLICY_EVALUATION_VERSION,
    POLICY_REGISTRY_VERSION, POLICY_AUDIT_VERSION, POLICY_LINEAGE_VERSION,
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
    "PolicyIdentity": EntityContract(
        "PolicyIdentity", POLICY_IDENTITY_VERSION, ("id", "category", "policy_key"),
        ("id matches /^policy\\+[0-9a-f]{16}$/", "id derives from category + policy_key"),
        "stable across re-declaration", "minting audited via policy creation", "n/a"),
    "PolicyRecord": EntityContract(
        "PolicyRecord", POLICY_DOMAIN_VERSION,
        ("policy_id", "category", "policy_key", "title", "subject_kind"),
        ("category in the closed policy taxonomy",
         "explainable: title + description present; no hidden logic",
         "only evaluates while ACTIVE; ACTIVE requires governance approval"),
        "chained hash(state, previous)", "creation/update/lifecycle/version audited",
        "parents reach the goals/governance artifacts it derives from"),
    "PolicyRule": EntityContract(
        "PolicyRule", POLICY_RULE_VERSION, ("rule_id", "fact", "operator"),
        ("operator in {eq,ne,in,not_in,exists,not_exists,ge,le,truthy}",
         "declarative predicate — no executable code"),
        "part of the policy/constraint state signature", "n/a", "n/a"),
    "ConstraintRecord": EntityContract(
        "ConstraintRecord", CONSTRAINT_VERSION,
        ("constraint_id", "constraint_type", "category", "subject_kind", "constraint_key"),
        ("constraint_type in {allowed,forbidden,required,escalated,deferred,conditional}",
         "explainable: every rule self-describes its outcome"),
        "content-addressed; versioned", "constraint changes audited",
        "constraint lineage parents its owning policy"),
    "ConstraintCategory": EntityContract(
        "ConstraintCategory", POLICY_TAXONOMY_VERSION, ("category",),
        ("category in the closed constraint-category vocabulary",),
        "closed vocabulary", "n/a", "n/a"),
    "PolicyEvaluation": EntityContract(
        "PolicyEvaluation", POLICY_EVALUATION_VERSION,
        ("evaluation_id", "policy_id", "request", "outcome"),
        ("outcome in {permitted,denied,requires_review,escalated,conditional_approval}",
         "deterministic; records applied rules + triggered constraints + evidence"),
        "content-addressed from policy + request", "evaluation events audited",
        "evaluation lineage parents the policy node and the subject node"),
    "PolicyVersion": EntityContract(
        "PolicyVersion", POLICY_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "PolicyAuditRecord": EntityContract(
        "PolicyAuditRecord", POLICY_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "PolicyLineageRecord": EntityContract(
        "PolicyLineageRecord", POLICY_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach upstream nodes (to the patient)"),
    "PolicyRegistryRecord": EntityContract(
        "PolicyRegistryRecord", POLICY_REGISTRY_VERSION,
        ("policy_id", "category", "state", "version", "lineage_id"),
        ("no policy exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current policy version", "registry changes audited",
        "lineage_id references the policy lineage node"),
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
    return {"policy_domain_version": POLICY_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
