"""Entity contracts for the Signal Processing domain (no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit
Rule. ``validate_entity`` checks an entity's serialized form against its schema.
Mirrors ``backend.eeg_foundation.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    SIGNAL_DOMAIN_VERSION, SIGNAL_IDENTITY_VERSION, SIGNAL_QUALITY_VERSION,
    SIGNAL_ARTIFACT_VERSION, SIGNAL_PREPROCESSING_VERSION, SIGNAL_STORAGE_VERSION,
    SIGNAL_REGISTRY_VERSION, SIGNAL_AUDIT_VERSION, SIGNAL_LINEAGE_VERSION,
    SIGNAL_REPORT_VERSION,
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
    "SignalIdentity": EntityContract(
        "SignalIdentity", SIGNAL_IDENTITY_VERSION, ("processed_id", "eeg_asset_id", "identity_version"),
        ("processed_id matches /^signal\\+[0-9a-f]{16}$/",
         "content-addressed from raw EEG asset id + processing fingerprint (never filename)"),
        "derived_from = eeg_asset_id", "minted-once; never modified"),
    "SignalRecord": EntityContract(
        "SignalRecord", SIGNAL_DOMAIN_VERSION,
        ("signal_kind", "n_channels", "sampling_frequency", "n_samples", "content_fingerprint"),
        ("signal_kind is raw|processed", "content_fingerprint is content-addressed"),
        "n/a (descriptor)", "n/a"),
    "SignalQualityRecord": EntityContract(
        "SignalQualityRecord", SIGNAL_QUALITY_VERSION,
        ("quality_id", "eeg_asset_id", "signal_kind", "recording_quality_score", "grade"),
        ("all scores in [0,1]", "grade derived from recording_quality_score",
         "deterministic (pure function of the signal)"),
        "n/a", "quality assessment audited"),
    "SignalArtifactRecord": EntityContract(
        "SignalArtifactRecord", SIGNAL_ARTIFACT_VERSION,
        ("artifact_id", "artifact_type", "severity", "confidence", "affected_channels",
         "onset_seconds", "duration_seconds"),
        ("artifact_type is a closed ArtifactType", "severity is a closed ArtifactSeverity",
         "confidence in [0,1]"),
        "n/a", "detection audited"),
    "SignalProcessingRecord": EntityContract(
        "SignalProcessingRecord", SIGNAL_PREPROCESSING_VERSION,
        ("processing_id", "eeg_asset_id", "steps", "input_fingerprint", "output_fingerprint"),
        ("deterministic + reproducible", "steps form a contiguous fingerprint chain",
         "raw EEG never mutated"),
        "n/a", "every step audited"),
    "FilterConfig": EntityContract(
        "FilterConfig", SIGNAL_PREPROCESSING_VERSION, ("filter_type", "params"),
        ("filter_type is a closed FilterType",), "n/a", "filter application audited"),
    "ProcessedEEGStorageRecord": EntityContract(
        "ProcessedEEGStorageRecord", SIGNAL_STORAGE_VERSION,
        ("storage_id", "processed_file_reference", "checksum_sha256", "content_fingerprint", "n_bytes"),
        ("checksum is the full sha256 of the stored processed bytes",
         "content-addressed local storage; no cloud/S3/db", "separate from the raw store"),
        "lineage_refs reference the processed lineage node", "storage event audited"),
    "ProcessedEEGMetadata": EntityContract(
        "ProcessedEEGMetadata", SIGNAL_DOMAIN_VERSION,
        ("n_channels", "sampling_frequency", "n_samples", "channel_labels", "quality_grade"),
        ("deterministic", "applied_filters/removal_methods recorded"),
        "n/a", "n/a"),
    "ProcessedEEGRecord": EntityContract(
        "ProcessedEEGRecord", SIGNAL_DOMAIN_VERSION,
        ("identity", "eeg_asset_id", "case_id", "patient_id", "raw_signal", "processed_signal",
         "quality", "processing", "storage", "status", "version"),
        ("status is a closed ProcessedAssetStatus", "carries no raw signal array",
         "derived from an immutable raw EEG asset"),
        "lineage node parents the raw EEG node (Patient -> Case -> EEG -> Processed)",
        "every processing/quality/artifact/storage/version/registration event audited"),
    "SignalRegistryRecord": EntityContract(
        "SignalRegistryRecord", SIGNAL_REGISTRY_VERSION,
        ("processed_id", "eeg_asset_id", "case_id", "patient_id", "status", "version", "lineage_id"),
        ("no processed asset exists outside the registry",
         "silent overwrite with different content forbidden"),
        "lineage_id references the processed lineage node", "registry changes audited"),
    "SignalAuditRecord": EntityContract(
        "SignalAuditRecord", SIGNAL_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "SignalLineageRecord": EntityContract(
        "SignalLineageRecord", SIGNAL_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the raw EEG lineage node", "lineage event audited"),
    "SignalReport": EntityContract(
        "SignalReport", SIGNAL_REPORT_VERSION, ("report_type", "signal_report_version"),
        ("deterministic; reproducible for a given asset/registry state",), "n/a", "n/a"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    """Check an entity's serialized form against its contract's required fields."""
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing
