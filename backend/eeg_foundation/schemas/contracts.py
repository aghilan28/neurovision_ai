"""Entity contracts for the EEG Foundation domain (Productization P1).

Each entity declares its schema (required fields), validation rules, version rule,
audit rule, and lineage rule. No undocumented objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    EEG_DOMAIN_VERSION, EEG_IDENTITY_VERSION, EEG_METADATA_VERSION, EEG_VALIDATION_VERSION,
    EEG_STORAGE_VERSION, EEG_REGISTRY_VERSION, EEG_AUDIT_VERSION, EEG_LINEAGE_VERSION,
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
    "EEGRecord": EntityContract(
        "EEGRecord", EEG_DOMAIN_VERSION,
        ("eeg_id", "format", "source", "metadata", "storage", "status"),
        ("format in {EDF, EDF+, BDF, BDF+, FIF, SET}",
         "eeg_id matches /^eeg\\+[0-9a-f]{16}$/ and derives from the file fingerprint",
         "a real file was read (no mocks); content-addressed"),
        "chained hash(state, previous)", "ingestion/validation/storage/version audited",
        "lineage parent is the Case node (Patient -> Case -> EEG Asset)"),
    "EEGMetadata": EntityContract(
        "EEGMetadata", EEG_METADATA_VERSION,
        ("recording_id", "format", "n_channels", "sampling_frequency"),
        ("deterministic (no wall-clock); stored independently of the raw file",
         "sampling_frequency > 0 for a valid asset"),
        "part of the EEG state signature", "extraction audited", "n/a"),
    "EEGSource": EntityContract(
        "EEGSource", EEG_DOMAIN_VERSION, ("original_filename", "format"),
        ("original_filename is for traceability only; never used to derive identity",),
        "part of the EEG state signature", "n/a", "n/a"),
    "EEGFormat": EntityContract(
        "EEGFormat", EEG_DOMAIN_VERSION, ("value",),
        ("closed vocabulary: EDF, EDF+, BDF, BDF+, FIF, SET",), "n/a", "n/a", "n/a"),
    "EEGChannel": EntityContract(
        "EEGChannel", EEG_DOMAIN_VERSION, ("label", "index", "sampling_frequency"),
        ("sampling_frequency >= 0; kind in {eeg, annotation, ...}",), "n/a", "n/a", "n/a"),
    "EEGChannelSet": EntityContract(
        "EEGChannelSet", EEG_DOMAIN_VERSION, ("channels",),
        ("ordered; count and labels derived from channels",),
        "part of the EEG state signature", "n/a", "n/a"),
    "EEGAnnotation": EntityContract(
        "EEGAnnotation", EEG_DOMAIN_VERSION, ("onset_seconds", "description"),
        ("onset_seconds >= 0 for a valid annotation",),
        "part of the EEG state signature", "n/a", "n/a"),
    "EEGValidationReport": EntityContract(
        "EEGValidationReport", EEG_VALIDATION_VERSION, ("results",),
        ("returns structured findings, never exceptions",
         "valid iff no error/critical findings"),
        "part of the EEG state signature", "validation audited", "n/a"),
    "EEGStorageRecord": EntityContract(
        "EEGStorageRecord", EEG_STORAGE_VERSION,
        ("storage_id", "backend", "location", "checksum_sha256", "fingerprint"),
        ("local only (no cloud/S3); stored by reference",
         "checksum + fingerprint deterministic from the bytes"),
        "part of the EEG state signature", "storage audited", "references the EEG lineage"),
    "EEGRegistryRecord": EntityContract(
        "EEGRegistryRecord", EEG_REGISTRY_VERSION,
        ("eeg_id", "format", "status", "version", "lineage_id"),
        ("no EEG asset exists outside the registry (no orphans)",
         "silent overwrite with different content forbidden"),
        "tracks the current EEG version", "registry changes audited",
        "lineage_id references the EEG asset node"),
    "EEGAuditRecord": EntityContract(
        "EEGAuditRecord", EEG_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)", "n/a"),
    "EEGLineageRecord": EntityContract(
        "EEGLineageRecord", EEG_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parent is the Case node; chain reaches the patient"),
    "EEGIdentity": EntityContract(
        "EEGIdentity", EEG_IDENTITY_VERSION, ("id", "format", "fingerprint"),
        ("id matches /^eeg\\+[0-9a-f]{16}$/; derived from format + fingerprint",),
        "stable across re-ingestion of the same file", "minting audited", "n/a"),
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
    return {"eeg_domain_version": EEG_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
