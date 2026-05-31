"""Execution-history persistence (DRP4-H).

Persists execution-history streams (training / benchmark / inference / serving / validation)
to durable storage and recovers them as ordered lists, supporting historical replay and
deterministic recovery. Stores already-serialized record dicts (no duplicated business logic).
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import ExecutionStorageRecord, StorageNamespace, StorageRecord
from ..storage import StorageEngine


class ExecutionStore:
    """Persists + recovers execution-history streams."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine

    def persist(self, history_kind: str, entries: Sequence
                ) -> tuple[StorageRecord, ExecutionStorageRecord]:
        ordered = [dict(e) for e in entries]
        snapshot = {"history_kind": history_kind, "n_entries": len(ordered), "entries": ordered}
        sr = self.engine.put(StorageNamespace.EXECUTION, history_kind, snapshot)
        esr = ExecutionStorageRecord(history_kind=history_kind, n_entries=len(ordered),
                                     fingerprint=sr.fingerprint, storage_id=sr.storage_id)
        return sr, esr

    def recover(self, storage_record: StorageRecord) -> list:
        snapshot = self.engine.get(storage_record.namespace, storage_record.key,
                                   expected_checksum=storage_record.checksum)
        return list(snapshot["entries"])


__all__ = ["ExecutionStore"]
