"""``backend/dataset_integration/schemas`` — entity contracts (DRP1-K).

A documented contract per entity (no undocumented objects): required fields + rules +
lineage/audit rules. ``validate_entity`` checks a serialized entity against its contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    DATASET_DOMAIN_VERSION, DATASET_GOVERNANCE_VERSION, DATASET_READINESS_VERSION,
    DATASET_REGISTRY_VERSION, DATASET_VALIDATION_VERSION, DATASET_AUDIT_VERSION,
    DATASET_LINEAGE_VERSION, DATASET_REPORT_VERSION, DATASET_INVENTORY_VERSION,
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
    "DatasetInventoryRecord": EntityContract(
        "DatasetInventoryRecord", DATASET_INVENTORY_VERSION,
        ("inventory_id", "source", "name", "format", "n_recordings"),
        ("source is a closed EegDatasetSource", "inventory only — never downloaded",
         "metadata_completeness in [0,1]"),
        "n/a", "inventory event audited"),
    "DatasetRecord": EntityContract(
        "DatasetRecord", DATASET_DOMAIN_VERSION,
        ("identity", "inventory", "version", "status", "manifest_fingerprint"),
        ("dataset_id = dataset+{hash16} content-addressed from source+manifest",
         "carries no recording arrays", "status is a closed InventoryStatus"),
        "lineage_id references the dataset/version node (Source->Dataset->Version)",
        "register/validate/govern/score events audited"),
    "DatasetSourceRecord": EntityContract(
        "DatasetSourceRecord", DATASET_DOMAIN_VERSION,
        ("source_id", "source", "display_name", "source_url"),
        ("source_id = dataset_source+{hash16}",),
        "source node is the lineage root", "source recorded"),
    "DatasetValidationRecord": EntityContract(
        "DatasetValidationRecord", DATASET_VALIDATION_VERSION,
        ("validation_id", "ok", "findings"),
        ("structured findings (check, severity, passed, detail); never exceptions",
         "ok iff no ERROR/CRITICAL finding failed"),
        "n/a", "validation recorded"),
    "DatasetGovernanceRecord": EntityContract(
        "DatasetGovernanceRecord", DATASET_GOVERNANCE_VERSION,
        ("governance_id", "license_name", "license_type", "status"),
        ("metadata only — no legal interpretation, no compliance claim",
         "license_type is a closed LicenseType"),
        "n/a", "governance recorded"),
    "DatasetReadinessRecord": EntityContract(
        "DatasetReadinessRecord", DATASET_READINESS_VERSION,
        ("readiness_id", "score", "classification", "dimensions"),
        ("classification is NOT_READY/PARTIALLY_READY/READY", "score in [0,1]"),
        "n/a", "readiness recorded"),
    "DatasetRegistryRecord": EntityContract(
        "DatasetRegistryRecord", DATASET_REGISTRY_VERSION,
        ("entity_kind", "entity_id", "status", "version", "lineage_id", "audit_state"),
        ("no orphan records (audit head + lineage node required)",
         "silent overwrite with different content forbidden"),
        "lineage_id references the entity's lineage node", "registry changes governed"),
    "DatasetAuditRecord": EntityContract(
        "DatasetAuditRecord", DATASET_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",),
        "n/a", "immutable; append-only; shared ImmutableAuditLog"),
    "DatasetLineageRecord": EntityContract(
        "DatasetLineageRecord", DATASET_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("recorded in the single shared LineageTracker (no parallel system)",),
        "Source -> Dataset -> Version chain", "lineage recorded"),
    "DatasetReport": EntityContract(
        "DatasetReport", DATASET_REPORT_VERSION, ("report_type", "dataset_report_version"),
        ("deterministic; reproducible for a given state",), "n/a", "n/a"),
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
