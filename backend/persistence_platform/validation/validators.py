"""Persistence content validation (DRP4-J, build-time).

Validates storage / registry / audit / lineage / execution / version integrity of a persisted
snapshot, producing structured ``(name, passed, detail)`` results — pure functions, no
exceptions.
"""

from __future__ import annotations

from typing import Sequence

from ..storage import StorageEngine


class PersistenceContentValidator:
    """Build-time validation of the persisted snapshot records."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine

    def storage_integrity(self, storage_records: Sequence) -> tuple[str, bool, dict]:
        ok = all(self.engine.verify(sr) for sr in storage_records)
        return ("storage_integrity", bool(ok), {"n_objects": len(storage_records)})

    def registry_integrity(self, registry_storage: Sequence) -> tuple[str, bool, dict]:
        ok = len(registry_storage) > 0 and all(r.fingerprint and r.n_records >= 0
                                               for r in registry_storage)
        return ("registry_integrity", bool(ok),
                {"registries": [r.registry_name for r in registry_storage]})

    def audit_integrity(self, audit_storage: Sequence) -> tuple[str, bool, dict]:
        ok = len(audit_storage) > 0 and all(a.head and a.n_events >= 0 for a in audit_storage)
        return ("audit_integrity", bool(ok), {"logs": [a.log_name for a in audit_storage]})

    def lineage_integrity(self, lineage_storage) -> tuple[str, bool, dict]:
        ok = lineage_storage.n_nodes > 0 and bool(lineage_storage.fingerprint)
        return ("lineage_integrity", bool(ok),
                {"n_nodes": lineage_storage.n_nodes, "n_edges": lineage_storage.n_edges})

    def execution_integrity(self, execution_storage: Sequence) -> tuple[str, bool, dict]:
        ok = all(e.n_entries >= 0 and e.fingerprint for e in execution_storage)
        return ("execution_integrity", bool(ok),
                {"streams": [e.history_kind for e in execution_storage]})

    def version_integrity(self, version_str: str) -> tuple[str, bool, dict]:
        return ("version_integrity", bool(version_str) and len(version_str) == 16,
                {"version": version_str})

    def content_checks(self, *, storage_records, registry_storage, audit_storage, lineage_storage,
                       execution_storage) -> list[tuple]:
        return [
            self.storage_integrity(storage_records),
            self.registry_integrity(registry_storage),
            self.audit_integrity(audit_storage),
            self.lineage_integrity(lineage_storage),
            self.execution_integrity(execution_storage),
        ]


__all__ = ["PersistenceContentValidator"]
