"""Registry persistence (DRP4-E).

Persists registry **snapshots** (the dataset / model / serving / readiness / validation
registries, each via its ``to_dict()``) to durable storage and recovers them. Version-aware
(the snapshot carries the registry's own version + counts), recoverable, and orphan-free (it
stores exactly what the registry reports — it adds and drops nothing).
"""

from __future__ import annotations

from typing import Mapping

from ..models.domain import RegistryStorageRecord, StorageNamespace, StorageRecord
from ..storage import StorageEngine


def _count_records(snapshot: Mapping) -> tuple[int, dict]:
    counts = dict(snapshot.get("counts", {})) if isinstance(snapshot.get("counts"), dict) else {}
    if counts:
        return sum(int(v) for v in counts.values()), counts
    # fall back to summing the obvious record collections in the snapshot
    total = 0
    derived = {}
    for k, v in snapshot.items():
        if isinstance(v, dict) and k not in ("counts",):
            derived[k] = len(v)
            total += len(v)
    return total, derived


class RegistryStore:
    """Persists + recovers registry snapshots."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine

    def persist(self, name: str, snapshot: Mapping) -> tuple[StorageRecord, RegistryStorageRecord]:
        sr = self.engine.put(StorageNamespace.REGISTRY, name, dict(snapshot))
        n_records, counts = _count_records(snapshot)
        rsr = RegistryStorageRecord(registry_name=name, n_records=n_records, counts=counts,
                                    fingerprint=sr.fingerprint, storage_id=sr.storage_id)
        return sr, rsr

    def recover(self, storage_record: StorageRecord) -> dict:
        return self.engine.get(storage_record.namespace, storage_record.key,
                               expected_checksum=storage_record.checksum)


__all__ = ["RegistryStore"]
