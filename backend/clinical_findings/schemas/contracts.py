"""Entity contracts for the clinical-findings domain.

Each entity declares its Schema · Version · Validation Rules · Version Rules ·
Audit Rules · Lineage Rules in one versioned object.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    FINDING_DOMAIN_VERSION, FINDING_IDENTITY_VERSION, FINDING_LIFECYCLE_VERSION,
    FINDING_EVIDENCE_VERSION, FINDING_INTERPRETATION_VERSION, FINDING_AUDIT_VERSION,
    FINDING_LINEAGE_VERSION, FINDING_REGISTRY_VERSION,
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
    "FindingIdentity": EntityContract(
        "FindingIdentity", FINDING_IDENTITY_VERSION, ("finding_id", "review_id", "case_id"),
        ("finding_id matches /^finding\\+[0-9a-f]{16}$/", "review_id is a valid review identity"),
        "immutable once minted", "minted-once event audited", "derived_from = review_id"),
    "FindingRecord": EntityContract(
        "FindingRecord", FINDING_DOMAIN_VERSION, ("observation",),
        ("observation non-empty", "no diagnosis/recommendation/probability fields"),
        "content-hashed into the finding version", "record changes audited", "n/a"),
    "FindingMetadata": EntityContract(
        "FindingMetadata", FINDING_DOMAIN_VERSION, ("deidentified",),
        ("deidentified is True", "no filenames/PHI"),
        "content-hashed into the finding version", "metadata changes audited", "n/a"),
    "FindingEvidence": EntityContract(
        "FindingEvidence", FINDING_EVIDENCE_VERSION,
        ("evidence_id", "finding_id", "evidence_type", "evidence_source", "evidence_version"),
        ("a finding must have >= 1 evidence", "evidence_source references a registered artifact",
         "evidence_confidence is recorded, never computed"),
        "evidence set hashed into the finding version", "evidence changes audited",
        "evidence node parents the source (e.g. inference) lineage node"),
    "FindingInterpretation": EntityContract(
        "FindingInterpretation", FINDING_INTERPRETATION_VERSION,
        ("interpretation_id", "finding_id", "interpretation_text"),
        ("kept SEPARATE from the finding (never merged)", "supporting_evidence references evidence ids",
         "confidence_level is qualitative + recorded"),
        "interpretation has its own version", "interpretation changes audited",
        "interpretation node parents the finding lineage node"),
    "FindingVersion": EntityContract(
        "FindingVersion", FINDING_DOMAIN_VERSION, ("version", "reason"),
        ("version = hash(state_signature, previous)", "previous links the prior version"),
        "chained per-finding hash", "version changes audited", "n/a"),
    "FindingAuditRecord": EntityContract(
        "FindingAuditRecord", FINDING_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "FindingLineageRecord": EntityContract(
        "FindingLineageRecord", FINDING_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage changes audited",
        "parents reach review/case/study/inference + evidence + interpretation nodes"),
    "FindingRegistryRecord": EntityContract(
        "FindingRegistryRecord", FINDING_REGISTRY_VERSION,
        ("finding_id", "case_id", "review_id", "status", "version", "lineage_id"),
        ("no finding exists outside the registry", "silent overwrite with different content forbidden",
         "evidence_ids non-empty"),
        "tracks the current finding version", "registry changes audited",
        "lineage_id references the finding lineage node"),
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
