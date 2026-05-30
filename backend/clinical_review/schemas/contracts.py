"""Entity contracts for the clinical-review domain.

Each entity declares its Schema · Contract · Version · Validation Rules · Lineage
Rules · Audit Rules in one versioned object.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    REVIEW_DOMAIN_VERSION, REVIEW_IDENTITY_VERSION, REVIEW_WORKFLOW_VERSION,
    REVIEW_SESSION_VERSION, REVIEW_ASSIGNMENT_VERSION, REVIEW_AUDIT_VERSION,
    REVIEW_LINEAGE_VERSION, REVIEW_REGISTRY_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    lineage_rule: str
    audit_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule}


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "ReviewIdentity": EntityContract(
        "ReviewIdentity", REVIEW_IDENTITY_VERSION, ("review_id", "case_id", "identity_version"),
        ("review_id matches /^review\\+[0-9a-f]{16}$/", "case_id is a valid case identity"),
        "derived_from = case_id", "minted-once; never modified"),
    "ReviewSession": EntityContract(
        "ReviewSession", REVIEW_SESSION_VERSION,
        ("session_id", "review_id", "reviewer", "session_start"),
        ("session belongs to its review", "artifacts/reports viewed are registered refs",
         "session_end >= session_start when closed"),
        "session node parents = review node + study/inference node", "session activity audited"),
    "ReviewAssignment": EntityContract(
        "ReviewAssignment", REVIEW_ASSIGNMENT_VERSION,
        ("assignment_id", "review_id", "assignee", "assignment_date", "priority", "status"),
        ("assignee is non-empty", "priority in {routine,urgent,stat}", "history preserved"),
        "n/a", "assignments + reassignments audited"),
    "ReviewStatus": EntityContract(
        "ReviewStatus", REVIEW_WORKFLOW_VERSION, ("status",),
        ("status is a valid ReviewStatus", "transitions follow the workflow machine"),
        "n/a", "every status change appended to audit log"),
    "ReviewHistory": EntityContract(
        "ReviewHistory", REVIEW_DOMAIN_VERSION, ("entries",),
        ("append-only", "ordered by occurrence"), "n/a", "mirrors audited status changes"),
    "ReviewAuditRecord": EntityContract(
        "ReviewAuditRecord", REVIEW_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident"),
    "ReviewLineageRecord": EntityContract(
        "ReviewLineageRecord", REVIEW_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference case + inference lineage nodes", "lineage changes audited"),
    "ReviewRegistryRecord": EntityContract(
        "ReviewRegistryRecord", REVIEW_REGISTRY_VERSION,
        ("review_id", "case_id", "version", "status", "lineage_id"),
        ("no review exists outside the registry", "silent overwrite with different content forbidden"),
        "lineage_id references the review lineage node", "registry changes audited"),
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
