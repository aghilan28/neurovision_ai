"""Entity contracts for the Persistence domain (DRP4-N; no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Recovery Rule · Audit Rule.
``validate_entity`` checks an entity's serialized form against its schema. Mirrors
``backend.serving_platform.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    PERSISTENCE_DOMAIN_VERSION, PERSISTENCE_IDENTITY_VERSION, PERSISTENCE_STORAGE_VERSION,
    PERSISTENCE_REPOSITORY_VERSION, PERSISTENCE_REGISTRY_STORAGE_VERSION,
    PERSISTENCE_AUDIT_STORAGE_VERSION, PERSISTENCE_LINEAGE_STORAGE_VERSION,
    PERSISTENCE_EXECUTION_STORAGE_VERSION, PERSISTENCE_RECOVERY_VERSION,
    PERSISTENCE_VALIDATION_VERSION, PERSISTENCE_READINESS_VERSION, PERSISTENCE_REPORT_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    recovery_rule: str
    audit_rule: str

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version,
            "required_fields": list(self.required_fields),
            "validation_rules": list(self.validation_rules),
            "recovery_rule": self.recovery_rule, "audit_rule": self.audit_rule,
        }


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "StorageRecord": EntityContract(
        "StorageRecord", PERSISTENCE_STORAGE_VERSION,
        ("storage_id", "namespace", "key", "checksum", "fingerprint", "uri"),
        ("canonical-JSON bytes; sha256 checksum + content fingerprint",
         "read verifies the checksum (tamper detection)"),
        "object is durable on the filesystem; survives cold restart", "n/a"),
    "RepositoryRecord": EntityContract(
        "RepositoryRecord", PERSISTENCE_REPOSITORY_VERSION,
        ("repository_kind", "n_records", "record_ids", "fingerprint", "storage_id"),
        ("typed repository over the storage engine; stores to_dict projections",
         "no duplicated business logic"),
        "records reload by id + checksum verify", "n/a"),
    "RegistryStorageRecord": EntityContract(
        "RegistryStorageRecord", PERSISTENCE_REGISTRY_STORAGE_VERSION,
        ("registry_name", "n_records", "counts", "fingerprint", "storage_id"),
        ("persists the registry's to_dict snapshot; version-aware; orphan-free",),
        "registry snapshot reloads + recomputes the same fingerprint", "registry persistence audited"),
    "AuditStorageRecord": EntityContract(
        "AuditStorageRecord", PERSISTENCE_AUDIT_STORAGE_VERSION,
        ("log_name", "n_events", "head", "fingerprint", "storage_id"),
        ("persists append-only events + chain head; immutable history",),
        "recovery replays events and reproduces the persisted head", "audit persistence audited"),
    "LineageStorageRecord": EntityContract(
        "LineageStorageRecord", PERSISTENCE_LINEAGE_STORAGE_VERSION,
        ("n_nodes", "n_edges", "fingerprint", "storage_id"),
        ("persists nodes + edges of the shared lineage graph",),
        "recovery rebuilds the tracker; verify_chain holds", "lineage persistence audited"),
    "ExecutionStorageRecord": EntityContract(
        "ExecutionStorageRecord", PERSISTENCE_EXECUTION_STORAGE_VERSION,
        ("history_kind", "n_entries", "fingerprint", "storage_id"),
        ("persists ordered execution-history streams (training/benchmark/inference/serving/"
         "validation)",),
        "recovery restores the ordered list for replay", "execution persistence audited"),
    "PersistenceValidationRecord": EntityContract(
        "PersistenceValidationRecord", PERSISTENCE_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("checks: storage/registry/audit/lineage/execution integrity",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "PersistenceReadinessRecord": EntityContract(
        "PersistenceReadinessRecord", PERSISTENCE_READINESS_VERSION,
        ("readiness_id", "target_id", "score", "classification", "dimensions"),
        ("six dimensions (storage/registry/recovery/audit/lineage/validation)",
         "READY requires all present + validation passes + recovery succeeds"),
        "n/a", "readiness audited"),
    "PersistenceRecord": EntityContract(
        "PersistenceRecord", PERSISTENCE_DOMAIN_VERSION,
        ("identity", "registry_storage", "audit_storage", "lineage_storage", "execution_storage",
         "repositories", "validation", "readiness_id", "status", "version"),
        ("immutable (frozen) once persisted",
         "binds registry + audit + lineage + execution storage under one snapshot fingerprint"),
        "the manifest enables full cold-restart recovery",
        "every persist/recover/validate/version event audited"),
    "PersistenceIdentity": EntityContract(
        "PersistenceIdentity", PERSISTENCE_IDENTITY_VERSION,
        ("persistence_id", "snapshot_fingerprint"),
        ("persistence_id matches /^persistence_record\\+[0-9a-f]{16}$/",
         "content-addressed from the snapshot"),
        "anchors the recovery event", "minted-once; never modified"),
    "RecoveryResult": EntityContract(
        "RecoveryResult", PERSISTENCE_RECOVERY_VERSION, ("recovery_id", "status"),
        ("cold-restart recovery of registries/audit/lineage/execution",
         "checksum-verified reads; rebuilt chains re-verified"),
        "the anchor chain verifies after recovery", "recovery event recorded in lineage + audit"),
    "PersistenceReport": EntityContract(
        "PersistenceReport", PERSISTENCE_REPORT_VERSION,
        ("report_type", "persistence_report_version"),
        ("deterministic; reproducible for a given record/recovery state",), "n/a", "n/a"),
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


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
