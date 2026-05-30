"""Entity contracts for the EEG Foundation domain.

For each entity the platform requires a declarative, versioned contract capturing:
Schema (required fields) · Validation Rules · Lineage Rule · Audit Rule.
``EntityContract`` captures these in one object; ``validate_entity`` checks an
entity's serialized form against its schema (required fields present + non-null).

Mirrors ``backend.clinical_cases.schemas.contracts`` so the EEG layer documents its
objects the same way the rest of the platform does (no undocumented objects).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    EEG_DOMAIN_VERSION, EEG_IDENTITY_VERSION, EEG_METADATA_VERSION,
    EEG_VALIDATION_VERSION, EEG_STORAGE_VERSION, EEG_REGISTRY_VERSION,
    EEG_AUDIT_VERSION, EEG_LINEAGE_VERSION,
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
    "EEGIdentity": EntityContract(
        "EEGIdentity", EEG_IDENTITY_VERSION, ("asset_id", "case_id", "identity_version"),
        ("asset_id matches /^eeg\\+[0-9a-f]{16}$/", "case_id is a valid case identity",
         "content-addressed from case + file fingerprint (never the filename)"),
        "derived_from = case_id", "minted-once; never modified"),
    "EEGRecord": EntityContract(
        "EEGRecord", EEG_DOMAIN_VERSION,
        ("identity", "case_id", "patient_id", "eeg_format", "source", "channel_set",
         "metadata", "storage", "validation", "status", "version"),
        ("eeg_format is one of EDF/EDF+/BDF/BDF+/FIF/SET", "status is a valid EEGAssetStatus",
         "carries no raw signal and no analytics"),
        "lineage node parents the case node (Patient -> Case -> EEG)",
        "every ingestion/validation/storage/version/registration event audited"),
    "EEGMetadata": EntityContract(
        "EEGMetadata", EEG_METADATA_VERSION,
        ("recording_id", "eeg_format", "duration_seconds", "sampling_frequency",
         "n_channels", "channel_labels"),
        ("deterministic (pure function of the parsed file)", "stored independently of raw bytes",
         "recording_id is content-addressed, not filename-derived"),
        "n/a (descriptive)", "metadata extraction audited"),
    "EEGSource": EntityContract(
        "EEGSource", EEG_DOMAIN_VERSION,
        ("original_filename", "detected_format", "file_size_bytes", "source_checksum_sha256"),
        ("detected_format determined from bytes", "original_filename is a basename only (no path)"),
        "n/a", "ingestion event records source facts"),
    "EEGFormat": EntityContract(
        "EEGFormat", EEG_DOMAIN_VERSION, ("value",),
        ("closed vocabulary: EDF, EDF+, BDF, BDF+, FIF, SET — no others",),
        "n/a", "n/a"),
    "EEGChannel": EntityContract(
        "EEGChannel", EEG_DOMAIN_VERSION, ("label", "channel_type"),
        ("channel_type is a normalized EEGChannelType", "sampling_frequency >= 0"),
        "n/a", "n/a"),
    "EEGChannelSet": EntityContract(
        "EEGChannelSet", EEG_DOMAIN_VERSION, ("channels",),
        ("count == len(channels)", "layout is a deterministic type histogram"),
        "n/a", "n/a"),
    "EEGAnnotation": EntityContract(
        "EEGAnnotation", EEG_DOMAIN_VERSION, ("onset_seconds", "duration_seconds", "description"),
        ("onset_seconds >= 0", "duration_seconds >= 0"),
        "n/a", "annotation anomalies surfaced as validation findings"),
    "EEGValidationResult": EntityContract(
        "EEGValidationResult", EEG_VALIDATION_VERSION, ("findings",),
        ("ok iff no ERROR/CRITICAL finding", "structured findings, never exceptions"),
        "n/a", "validation event records the result signature"),
    "EEGValidationFinding": EntityContract(
        "EEGValidationFinding", EEG_VALIDATION_VERSION, ("code", "severity", "message"),
        ("severity is a valid EEGValidationSeverity",),
        "n/a", "n/a"),
    "EEGStorageRecord": EntityContract(
        "EEGStorageRecord", EEG_STORAGE_VERSION,
        ("storage_id", "raw_file_reference", "eeg_format", "checksum_sha256",
         "content_fingerprint", "file_size_bytes", "version"),
        ("checksum is the full sha256 of the stored bytes", "content-addressed local storage",
         "no cloud/S3/database"),
        "lineage_refs reference the EEG lineage node", "storage event audited"),
    "EEGAuditRecord": EntityContract(
        "EEGAuditRecord", EEG_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "EEGLineageRecord": EntityContract(
        "EEGLineageRecord", EEG_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the case lineage node", "lineage event audited"),
    "EEGRegistryRecord": EntityContract(
        "EEGRegistryRecord", EEG_REGISTRY_VERSION,
        ("asset_id", "case_id", "patient_id", "eeg_format", "status", "version", "lineage_id"),
        ("no asset exists outside the registry", "silent overwrite with different content forbidden"),
        "lineage_id references the EEG lineage node", "registry changes audited"),
    "IngestionOutcome": EntityContract(
        "IngestionOutcome", EEG_DOMAIN_VERSION, ("accepted", "reason", "validation"),
        ("accepted assets carry an EEGRecord", "rejected files still carry validation findings"),
        "n/a", "n/a"),
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
