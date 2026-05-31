"""``backend/persistence_platform`` — Persistence Platform (DRP-4).

Closes the audit's *no persistence layer* blocker: turns the in-memory platform into a
**persistent platform** with durable storage, persistent registries, and durable audit /
lineage / execution history that survives a cold restart. The scope is *persistence* and
nothing else:

    persist registries + audit + lineage + execution -> recover state (cold restart) ->
    validate recovery -> score persistence readiness -> trace + audit

No model / training / inference / serving / frontend / deployment / monitoring / security
changes (all out of scope) — it persists and recovers state without modifying business logic.

Built strictly on the existing platform: it **reuses** (serializes + faithfully reconstructs)
the shared ``ml.lineage`` tracker and the shared ``ImmutableAuditLog`` — **no parallel audit
or lineage systems** — and persists the DRP-1/DRP-2/DRP-3 registries (dataset / model /
serving / readiness / validation). A persistence record's lineage parents a representative
served execution (the anchor); a recovery event parents the persistence record — so a single
``verify_chain`` proves

    Dataset -> Model -> Inference -> Serving -> Persistence Record -> Recovery Event.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` only; never ``frontend``. Durable storage is local-filesystem JSON (deterministic,
checksum-verified); no cloud/database/deployment. Tests live in the repository-root ``tests/``
(``tests/test_persistence_platform*.py``).
"""

from __future__ import annotations

from .version import (
    PERSISTENCE_PLATFORM_VERSION, PERSISTENCE_DOMAIN_VERSION, PERSISTENCE_IDENTITY_VERSION,
    PERSISTENCE_STORAGE_VERSION, PERSISTENCE_REPOSITORY_VERSION, PERSISTENCE_REGISTRY_STORAGE_VERSION,
    PERSISTENCE_AUDIT_STORAGE_VERSION, PERSISTENCE_LINEAGE_STORAGE_VERSION,
    PERSISTENCE_EXECUTION_STORAGE_VERSION, PERSISTENCE_RECOVERY_VERSION,
    PERSISTENCE_VALIDATION_VERSION, PERSISTENCE_READINESS_VERSION, PERSISTENCE_AUDIT_VERSION,
    PERSISTENCE_LINEAGE_VERSION, PERSISTENCE_REPORT_VERSION,
)
from .models import (
    StorageNamespace, RepositoryKind, PersistenceStatus, RecoveryStatus, ReadinessClass,
    ReadinessDimension, EntityKind, PersistenceIdentity, StorageVersion, StorageRecord,
    RepositoryRecord, RegistryStorageRecord, AuditStorageRecord, LineageStorageRecord,
    ExecutionStorageRecord, PersistenceValidationRecord, PersistenceReadinessRecord,
    PersistenceAuditRecord, PersistenceLineageRecord, PersistenceRecord,
)
from .identity import Identity, IdentityError, mint_identity, validate_identity
from .storage import StorageEngine, StorageError
from .repositories import Repository, RepositoryError
from .registry_storage import RegistryStore
from .audit_storage import AuditStore, AuditPersistenceError
from .lineage_storage import LineageStore
from .execution_storage import ExecutionStore
from .lifecycle import RecoveryEngine, RecoveryResult
from .validation import PersistenceContentValidator, PersistenceIntegrityValidator
from .readiness import PersistenceReadinessEngine
from .audit import make_persistence_audit_log, ImmutableAuditLog, AuditError
from .lineage import make_persistence_lineage, make_recovery_lineage
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import (
    PersistencePlatformService, PlatformState, PersistenceOutcome, PersistencePlatformError,
)

__all__ = [
    # versions
    "PERSISTENCE_PLATFORM_VERSION", "PERSISTENCE_DOMAIN_VERSION", "PERSISTENCE_IDENTITY_VERSION",
    "PERSISTENCE_STORAGE_VERSION", "PERSISTENCE_REPOSITORY_VERSION",
    "PERSISTENCE_REGISTRY_STORAGE_VERSION", "PERSISTENCE_AUDIT_STORAGE_VERSION",
    "PERSISTENCE_LINEAGE_STORAGE_VERSION", "PERSISTENCE_EXECUTION_STORAGE_VERSION",
    "PERSISTENCE_RECOVERY_VERSION", "PERSISTENCE_VALIDATION_VERSION", "PERSISTENCE_READINESS_VERSION",
    "PERSISTENCE_AUDIT_VERSION", "PERSISTENCE_LINEAGE_VERSION", "PERSISTENCE_REPORT_VERSION",
    # models / vocab
    "StorageNamespace", "RepositoryKind", "PersistenceStatus", "RecoveryStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "PersistenceIdentity", "StorageVersion", "StorageRecord",
    "RepositoryRecord", "RegistryStorageRecord", "AuditStorageRecord", "LineageStorageRecord",
    "ExecutionStorageRecord", "PersistenceValidationRecord", "PersistenceReadinessRecord",
    "PersistenceAuditRecord", "PersistenceLineageRecord", "PersistenceRecord",
    # identity
    "Identity", "IdentityError", "mint_identity", "validate_identity",
    # storage / repositories / stores
    "StorageEngine", "StorageError", "Repository", "RepositoryError", "RegistryStore", "AuditStore",
    "AuditPersistenceError", "LineageStore", "ExecutionStore",
    # recovery / validation / readiness / audit / lineage / schemas
    "RecoveryEngine", "RecoveryResult", "PersistenceContentValidator",
    "PersistenceIntegrityValidator", "PersistenceReadinessEngine", "make_persistence_audit_log",
    "ImmutableAuditLog", "AuditError", "make_persistence_lineage", "make_recovery_lineage",
    "ENTITY_CONTRACTS", "validate_entity",
    # service
    "PersistencePlatformService", "PlatformState", "PersistenceOutcome", "PersistencePlatformError",
]
