"""Entity contracts for the clinical-case domain.

For each entity the directive requires: Schema · Contract · Version · Validation
Rules · Lineage Rules · Audit Rules. ``EntityContract`` captures all six in a
single declarative, versioned object; ``validate_entity`` checks an entity's
serialized form against its schema (required fields present + non-null).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    CASE_DOMAIN_VERSION, CASE_IDENTITY_VERSION, CASE_LIFECYCLE_VERSION,
    CASE_AUDIT_VERSION, CASE_LINEAGE_VERSION, CASE_REGISTRY_VERSION,
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
        return {
            "name": self.name, "version": self.version,
            "required_fields": list(self.required_fields),
            "validation_rules": list(self.validation_rules),
            "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule,
        }


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "PatientIdentity": EntityContract(
        "PatientIdentity", CASE_IDENTITY_VERSION, ("patient_id", "identity_version"),
        ("patient_id matches /^patient\\+[0-9a-f]{16}$/", "deidentified key only (no PHI)"),
        "root of identity lineage (no parent)", "minted-once; never modified"),
    "CaseIdentity": EntityContract(
        "CaseIdentity", CASE_IDENTITY_VERSION, ("case_id", "patient_id", "identity_version"),
        ("case_id matches /^case\\+[0-9a-f]{16}$/", "patient_id is a valid patient identity"),
        "derived_from = patient_id", "minted-once; never modified"),
    "StudyIdentity": EntityContract(
        "StudyIdentity", CASE_IDENTITY_VERSION, ("study_id", "case_id", "identity_version"),
        ("study_id matches /^study\\+[0-9a-f]{16}$/", "case_id is a valid case identity",
         "inference_id (if present) references a registered V1 inference"),
        "derived_from = case_id; references V1 inference lineage", "study-attach event audited"),
    "CaseMetadata": EntityContract(
        "CaseMetadata", CASE_DOMAIN_VERSION, ("modality", "deidentified"),
        ("deidentified is True", "no filenames or folder paths"),
        "n/a (descriptive)", "metadata changes audited as modifications"),
    "CaseState": EntityContract(
        "CaseState", CASE_LIFECYCLE_VERSION, ("status", "entered_at"),
        ("status is a valid CaseStatus", "transition_count >= 0"),
        "n/a", "every state change appended to audit log"),
    "CaseAuditRecord": EntityContract(
        "CaseAuditRecord", CASE_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident chain"),
    "CaseLineageRecord": EntityContract(
        "CaseLineageRecord", CASE_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference patient/case/study/inference lineage nodes",
        "lineage changes audited"),
    "CaseVersion": EntityContract(
        "CaseVersion", CASE_DOMAIN_VERSION, ("version", "reason"),
        ("version is a content hash of case state", "previous links to the prior version"),
        "n/a", "version changes audited"),
    "CaseRegistryRecord": EntityContract(
        "CaseRegistryRecord", CASE_REGISTRY_VERSION,
        ("case_id", "patient_id", "status", "version", "owner", "lineage_id"),
        ("no case exists outside the registry", "silent overwrite with different content forbidden"),
        "lineage_id references the case lineage node", "registry changes audited"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    """Check an entity's serialized form against its contract's required fields.

    Returns ``(ok, missing_fields)``.
    """
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing
