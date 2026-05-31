"""Persistence Platform domain model (DRP4-B) — closed vocabularies + records."""

from __future__ import annotations

from .domain import (
    StorageNamespace, RepositoryKind, PersistenceStatus, RecoveryStatus, ReadinessClass,
    ReadinessDimension, EntityKind, PersistenceIdentity, StorageVersion, StorageRecord,
    RepositoryRecord, RegistryStorageRecord, AuditStorageRecord, LineageStorageRecord,
    ExecutionStorageRecord, PersistenceValidationRecord, PersistenceReadinessRecord,
    PersistenceAuditRecord, PersistenceLineageRecord, PersistenceRecord,
)

__all__ = [
    "StorageNamespace", "RepositoryKind", "PersistenceStatus", "RecoveryStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "PersistenceIdentity", "StorageVersion", "StorageRecord",
    "RepositoryRecord", "RegistryStorageRecord", "AuditStorageRecord", "LineageStorageRecord",
    "ExecutionStorageRecord", "PersistenceValidationRecord", "PersistenceReadinessRecord",
    "PersistenceAuditRecord", "PersistenceLineageRecord", "PersistenceRecord",
]
