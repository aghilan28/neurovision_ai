"""Lineage persistence (DRP4-G).

Persists the shared lineage graph (nodes + edges + metadata) to durable storage and recovers
it by rebuilding a :class:`ml.lineage.LineageTracker` from the persisted nodes — preserving
chain integrity (every parent edge is restored) so ``verify_chain`` holds after recovery. No
parallel lineage system: it serializes and restores the **shared** tracker's nodes.
"""

from __future__ import annotations

from ml.lineage import LineageRecord, LineageTracker  # reuse the shared lineage machinery

from ..models.domain import LineageStorageRecord, StorageNamespace, StorageRecord
from ..storage import StorageEngine


class LineageStore:
    """Persists + recovers the shared lineage graph."""

    def __init__(self, engine: StorageEngine):
        self.engine = engine

    def persist(self, tracker: LineageTracker, *, key: str = "graph"
                ) -> tuple[StorageRecord, LineageStorageRecord]:
        nodes = tracker.all()
        n_edges = sum(len(rec.parents) for rec in nodes.values())
        snapshot = {
            "n_nodes": len(nodes), "n_edges": n_edges,
            "records": {lid: rec.to_dict() for lid, rec in sorted(nodes.items())},
        }
        sr = self.engine.put(StorageNamespace.LINEAGE, key, snapshot)
        lsr = LineageStorageRecord(n_nodes=len(nodes), n_edges=n_edges, fingerprint=sr.fingerprint,
                                   storage_id=sr.storage_id)
        return sr, lsr

    def recover(self, storage_record: StorageRecord) -> LineageTracker:
        snapshot = self.engine.get(storage_record.namespace, storage_record.key,
                                   expected_checksum=storage_record.checksum)
        tracker = LineageTracker()
        for _lid, node in sorted(snapshot["records"].items()):
            tracker.record(LineageRecord(
                lineage_id=node["lineage_id"], kind=node["kind"], versions=node["versions"],
                inputs=node["inputs"], outputs=node["outputs"], parents=tuple(node["parents"]),
                created_at=node["created_at"],
                lineage_version=node.get("lineage_version", LineageRecord.lineage_version)))
        return tracker


__all__ = ["LineageStore"]
