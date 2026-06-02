"""Persistence Platform domain entities + closed vocabularies (DRP4-B).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no business
logic — this module owns only the *shapes* and the *closed vocabularies* (no free-form
states). The storage engine / repositories / registry-audit-lineage-execution stores /
recovery engine produce these records; the service assembles the immutable
``PersistenceRecord`` aggregate.

Mirrors ``backend.serving_platform.models.domain`` so the persistence layer is shaped
exactly like the rest of the platform (NR-6). Determinism (NR-9/NR-10): every
``signature()`` and content id is a function of deterministic fields only — there is no
wall-clock and no randomness in the persistence path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    PERSISTENCE_DOMAIN_VERSION, PERSISTENCE_STORAGE_VERSION, PERSISTENCE_REPOSITORY_VERSION,
    PERSISTENCE_REGISTRY_STORAGE_VERSION, PERSISTENCE_AUDIT_STORAGE_VERSION,
    PERSISTENCE_LINEAGE_STORAGE_VERSION, PERSISTENCE_EXECUTION_STORAGE_VERSION,
    PERSISTENCE_READINESS_VERSION, PERSISTENCE_VALIDATION_VERSION, DETERMINISTIC_EPOCH,
    FINGERPRINT_DECIMALS,
)


def _q(x) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class StorageNamespace(str, Enum):
    """The closed set of durable storage namespaces."""

    REGISTRY = "registry"
    AUDIT = "audit"
    LINEAGE = "lineage"
    EXECUTION = "execution"
    REPOSITORY = "repository"
    SNAPSHOT = "snapshot"


class RepositoryKind(str, Enum):
    """The closed set of typed repositories (DRP4-D)."""

    DATASET = "dataset"
    MODEL = "model"
    TRAINING_RUN = "training_run"
    BENCHMARK = "benchmark"
    INFERENCE = "inference"
    SERVING = "serving"
    AUDIT = "audit"
    LINEAGE = "lineage"


class PersistenceStatus(str, Enum):
    PERSISTED = "persisted"
    FAILED = "failed"


class RecoveryStatus(str, Enum):
    RECOVERED = "recovered"
    PARTIAL = "partial"
    FAILED = "failed"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class ReadinessDimension(str, Enum):
    """The closed set of persistence-readiness dimensions (DRP4-K)."""

    STORAGE = "storage_readiness"
    REGISTRY = "registry_readiness"
    RECOVERY = "recovery_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"
    VALIDATION = "validation_readiness"


class EntityKind(str, Enum):
    """The kinds of entity tracked by the persistence platform."""

    PERSISTENCE_RECORD = "persistence_record"
    STORAGE = "storage"
    REPOSITORY = "repository"
    REGISTRY_STORAGE = "registry_storage"
    AUDIT_STORAGE = "audit_storage"
    LINEAGE_STORAGE = "lineage_storage"
    EXECUTION_STORAGE = "execution_storage"
    READINESS = "persistence_readiness"


# =============================================================================
# Identity + versioning projections
# =============================================================================
@dataclass(frozen=True)
class PersistenceIdentity:
    """A persistence-record identity, content-addressed from the persisted snapshot."""

    persistence_id: str
    snapshot_fingerprint: str
    anchor_lineage_id: Optional[str]
    identity_version: str
    domain_version: str = PERSISTENCE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "persistence_id": self.persistence_id, "snapshot_fingerprint": self.snapshot_fingerprint,
            "anchor_lineage_id": self.anchor_lineage_id, "identity_version": self.identity_version,
            "domain_version": self.domain_version,
        }


@dataclass(frozen=True)
class StorageVersion:
    """A content-addressed persistence-record version."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# Storage + repository records
# =============================================================================
@dataclass(frozen=True)
class StorageRecord:
    """One durably-stored object: namespace + key + checksum + content fingerprint."""

    storage_id: str
    namespace: str
    key: str
    checksum: str
    fingerprint: str
    size_bytes: int
    uri: str
    created_at: str = DETERMINISTIC_EPOCH
    storage_version: str = PERSISTENCE_STORAGE_VERSION

    def signature(self) -> str:
        return hash_obj({"storage_id": self.storage_id, "namespace": self.namespace,
                         "key": self.key, "checksum": self.checksum, "fingerprint": self.fingerprint,
                         "size_bytes": self.size_bytes})

    def to_dict(self) -> dict:
        return {
            "storage_id": self.storage_id, "namespace": self.namespace, "key": self.key,
            "checksum": self.checksum, "fingerprint": self.fingerprint, "size_bytes": self.size_bytes,
            "uri": self.uri, "created_at": self.created_at, "storage_version": self.storage_version,
            "storage_signature": self.signature(),
        }


@dataclass(frozen=True)
class RepositoryRecord:
    """A typed repository manifest: which record ids it durably holds."""

    repository_kind: str
    n_records: int
    record_ids: tuple[str, ...]
    fingerprint: str
    storage_id: str
    repository_version: str = PERSISTENCE_REPOSITORY_VERSION

    def signature(self) -> str:
        return hash_obj({"repository_kind": self.repository_kind, "n_records": self.n_records,
                         "record_ids": list(self.record_ids), "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {
            "repository_kind": self.repository_kind, "n_records": self.n_records,
            "record_ids": list(self.record_ids), "fingerprint": self.fingerprint,
            "storage_id": self.storage_id, "repository_version": self.repository_version,
            "repository_signature": self.signature(),
        }


@dataclass(frozen=True)
class RegistryStorageRecord:
    """A persisted registry snapshot."""

    registry_name: str
    n_records: int
    counts: dict
    fingerprint: str
    storage_id: str
    registry_storage_version: str = PERSISTENCE_REGISTRY_STORAGE_VERSION

    def signature(self) -> str:
        return hash_obj({"registry_name": self.registry_name, "n_records": self.n_records,
                         "counts": dict(sorted(self.counts.items())), "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {
            "registry_name": self.registry_name, "n_records": self.n_records,
            "counts": dict(sorted(self.counts.items())), "fingerprint": self.fingerprint,
            "storage_id": self.storage_id, "registry_storage_version": self.registry_storage_version,
            "registry_storage_signature": self.signature(),
        }


@dataclass(frozen=True)
class AuditStorageRecord:
    """A persisted, append-only audit log (events + chain head)."""

    log_name: str
    n_events: int
    head: str
    fingerprint: str
    storage_id: str
    audit_storage_version: str = PERSISTENCE_AUDIT_STORAGE_VERSION

    def signature(self) -> str:
        return hash_obj({"log_name": self.log_name, "n_events": self.n_events, "head": self.head,
                         "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {
            "log_name": self.log_name, "n_events": self.n_events, "head": self.head,
            "fingerprint": self.fingerprint, "storage_id": self.storage_id,
            "audit_storage_version": self.audit_storage_version,
            "audit_storage_signature": self.signature(),
        }


@dataclass(frozen=True)
class LineageStorageRecord:
    """A persisted lineage graph (nodes + edges)."""

    n_nodes: int
    n_edges: int
    fingerprint: str
    storage_id: str
    lineage_storage_version: str = PERSISTENCE_LINEAGE_STORAGE_VERSION

    def signature(self) -> str:
        return hash_obj({"n_nodes": self.n_nodes, "n_edges": self.n_edges,
                         "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {
            "n_nodes": self.n_nodes, "n_edges": self.n_edges, "fingerprint": self.fingerprint,
            "storage_id": self.storage_id, "lineage_storage_version": self.lineage_storage_version,
            "lineage_storage_signature": self.signature(),
        }


@dataclass(frozen=True)
class ExecutionStorageRecord:
    """A persisted execution-history stream (training / benchmark / inference / serving /
    validation)."""

    history_kind: str
    n_entries: int
    fingerprint: str
    storage_id: str
    execution_storage_version: str = PERSISTENCE_EXECUTION_STORAGE_VERSION

    def signature(self) -> str:
        return hash_obj({"history_kind": self.history_kind, "n_entries": self.n_entries,
                         "fingerprint": self.fingerprint})

    def to_dict(self) -> dict:
        return {
            "history_kind": self.history_kind, "n_entries": self.n_entries,
            "fingerprint": self.fingerprint, "storage_id": self.storage_id,
            "execution_storage_version": self.execution_storage_version,
            "execution_storage_signature": self.signature(),
        }


# =============================================================================
# Validation / readiness projections
# =============================================================================
@dataclass(frozen=True)
class PersistenceValidationRecord:
    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = PERSISTENCE_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok, "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {
            "validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "validation_version": self.validation_version, "validation_signature": self.signature(),
        }


@dataclass(frozen=True)
class PersistenceReadinessRecord:
    readiness_id: str
    target_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple[str, ...]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = PERSISTENCE_READINESS_VERSION

    def signature(self) -> str:
        return hash_obj({
            "readiness_id": self.readiness_id, "target_id": self.target_id, "score": _q(self.score),
            "classification": self.classification.value,
            "dimensions": {k: _q(v) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings),
        })

    def to_dict(self) -> dict:
        return {
            "readiness_id": self.readiness_id, "target_id": self.target_id, "score": _q(self.score),
            "classification": self.classification.value,
            "dimensions": {k: _q(v) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "readiness_version": self.readiness_version,
            "readiness_signature": self.signature(),
        }


# =============================================================================
# Audit / lineage projections
# =============================================================================
@dataclass(frozen=True)
class PersistenceAuditRecord:
    """An immutable audit event in the hash-chained persistence audit log (the shared
    ``ImmutableAuditLog`` implementation; no parallel system)."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "kind": self.kind, "payload": self.payload,
            "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at,
        }


@dataclass(frozen=True)
class PersistenceLineageRecord:
    """A projection of a shared lineage node attached to a persistence artifact."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# =============================================================================
# The aggregate — the immutable Persistence Record
# =============================================================================
@dataclass(frozen=True)
class PersistenceRecord:
    """The persistence aggregate — an **immutable**, versioned, auditable, lineage-tracked
    record of one durably-persisted platform snapshot. Binds the registry / audit / lineage
    / execution storage records (+ repository manifests) under one snapshot fingerprint."""

    identity: PersistenceIdentity
    registry_storage: tuple[RegistryStorageRecord, ...]
    audit_storage: tuple[AuditStorageRecord, ...]
    lineage_storage: LineageStorageRecord
    execution_storage: tuple[ExecutionStorageRecord, ...]
    repositories: tuple[RepositoryRecord, ...]
    storage_root: str
    validation: PersistenceValidationRecord
    readiness_id: str
    readiness_class: ReadinessClass
    status: PersistenceStatus
    version: StorageVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = PERSISTENCE_DOMAIN_VERSION

    @property
    def persistence_id(self) -> str:
        return self.identity.persistence_id

    @staticmethod
    def state_signature_of(*, identity, registry_storage, audit_storage, lineage_storage,
                           execution_storage, repositories, validation, readiness_id,
                           readiness_class, status, dependencies) -> str:
        return hash_obj({
            "persistence_id": identity.persistence_id,
            "snapshot_fingerprint": identity.snapshot_fingerprint,
            "registry_storage": [r.signature() for r in registry_storage],
            "audit_storage": [a.signature() for a in audit_storage],
            "lineage_storage": lineage_storage.signature(),
            "execution_storage": [e.signature() for e in execution_storage],
            "repositories": [r.signature() for r in repositories],
            "validation_signature": validation.signature(), "readiness_id": readiness_id,
            "readiness_class": readiness_class.value, "status": status.value,
            "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, registry_storage=self.registry_storage,
            audit_storage=self.audit_storage, lineage_storage=self.lineage_storage,
            execution_storage=self.execution_storage, repositories=self.repositories,
            validation=self.validation, readiness_id=self.readiness_id,
            readiness_class=self.readiness_class, status=self.status, dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "registry_storage": [r.to_dict() for r in self.registry_storage],
            "audit_storage": [a.to_dict() for a in self.audit_storage],
            "lineage_storage": self.lineage_storage.to_dict(),
            "execution_storage": [e.to_dict() for e in self.execution_storage],
            "repositories": [r.to_dict() for r in self.repositories], "storage_root": self.storage_root,
            "validation": self.validation.to_dict(), "readiness_id": self.readiness_id,
            "readiness_class": self.readiness_class.value, "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
