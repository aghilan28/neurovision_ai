"""``backend/dataset_acquisition/schemas`` — entity contracts (Track 1).

A documented contract per entity (no undocumented objects): required fields + rules +
lineage/audit rules. ``validate_entity`` checks a serialized entity against its contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    ACQUISITION_DOMAIN_VERSION, ACQUISITION_INVENTORY_VERSION, ACQUISITION_LABELS_VERSION,
    ACQUISITION_READINESS_VERSION, ACQUISITION_REGISTRY_VERSION, ACQUISITION_REPORT_VERSION,
    ACQUISITION_SOURCES_VERSION, ACQUISITION_STORAGE_VERSION, ACQUISITION_VALIDATION_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple
    rules: tuple
    lineage_rule: str
    audit_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields), "rules": list(self.rules),
                "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule}


ENTITY_CONTRACTS: dict = {
    "AcquisitionSourceSpec": EntityContract(
        "AcquisitionSourceSpec", ACQUISITION_SOURCES_VERSION,
        ("source", "official_source", "download_mechanism", "access_requirement"),
        ("source is a closed DatasetSource",
         "only OPEN + auto_downloadable corpora are auto-downloaded",
         "registration/restricted corpora are reported, never downloaded"),
        "n/a", "acquisition planned"),
    "AcquisitionRecord": EntityContract(
        "AcquisitionRecord", ACQUISITION_STORAGE_VERSION,
        ("source", "spec_signature", "attempted", "items"),
        ("items carry checksums (deterministic); never download timings",
         "approval-gated corpora have attempted=False"),
        "n/a", "acquire events audited"),
    "LocalFileRecord": EntityContract(
        "LocalFileRecord", ACQUISITION_STORAGE_VERSION,
        ("relative_path", "checksum_sha256", "state"),
        ("state is a closed AvailabilityState", "checksum is the real sha256 of the bytes"),
        "n/a", "verification audited"),
    "RecordingRecord": EntityContract(
        "RecordingRecord", ACQUISITION_DOMAIN_VERSION,
        ("recording_id", "patient_id", "relative_path", "checksum_sha256"),
        ("recording_id = recording+{hash16} from the real file (eeg_foundation)",
         "read from the ACTUAL file via the shared MNE reader; never a manifest"),
        "recording node parents the patient node", "connect audited"),
    "LabelRecord": EntityContract(
        "LabelRecord", ACQUISITION_LABELS_VERSION,
        ("label_id", "recording_id", "scheme", "value"),
        ("value is a closed LabelValue", "derived from real source annotations (no synthetic)",
         "scheme is a closed LabelScheme"),
        "label node parents the recording node", "label extraction audited"),
    "StructureValidationRecord": EntityContract(
        "StructureValidationRecord", ACQUISITION_VALIDATION_VERSION,
        ("validation_id", "ok", "findings"),
        ("structured findings (check, severity, passed, detail); never exceptions",
         "ok iff no ERROR/CRITICAL finding failed"),
        "n/a", "validation recorded"),
    "LabelVerificationRecord": EntityContract(
        "LabelVerificationRecord", ACQUISITION_LABELS_VERSION,
        ("verification_id", "scheme", "coverage", "n_classes"),
        ("coverage in [0,1]", "consistent requires real, single, in-scheme labels"),
        "n/a", "label verification recorded"),
    "InventoryRecord": EntityContract(
        "InventoryRecord", ACQUISITION_INVENTORY_VERSION,
        ("inventory_id", "source", "n_recordings", "n_patients"),
        ("actual counts from the connected real dataset",),
        "n/a", "inventory recorded"),
    "TrainingReadinessRecord": EntityContract(
        "TrainingReadinessRecord", ACQUISITION_READINESS_VERSION,
        ("readiness_id", "score", "classification", "dimensions"),
        ("classification is NOT_READY/PARTIALLY_READY/READY_FOR_TRAINING", "score in [0,1]",
         "READY_FOR_TRAINING requires real complete multi-class labels + verified files"),
        "n/a", "readiness recorded"),
    "RealDatasetRecord": EntityContract(
        "RealDatasetRecord", ACQUISITION_DOMAIN_VERSION,
        ("dataset_id", "source", "local_root", "content_fingerprint"),
        ("dataset_id = real_dataset+{hash16} content-addressed from real file checksums",
         "carries no recording arrays", "availability_state is a closed AvailabilityState"),
        "Source -> Dataset -> Patient -> Recording -> Label -> Registry",
        "acquire/connect/validate/label/inventory/score/register events audited"),
    "AcquisitionRegistryRecord": EntityContract(
        "AcquisitionRegistryRecord", ACQUISITION_REGISTRY_VERSION,
        ("entity_kind", "entity_id", "version", "lineage_id", "audit_state"),
        ("no orphan records (audit head + lineage node required)",
         "silent overwrite with different content forbidden"),
        "lineage_id references the entity's lineage node", "registry changes governed"),
    "AcquisitionReport": EntityContract(
        "AcquisitionReport", ACQUISITION_REPORT_VERSION,
        ("report_type", "acquisition_report_version"),
        ("deterministic; reproducible for a given local dataset state",), "n/a", "n/a"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
