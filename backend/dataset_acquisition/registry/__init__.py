"""``backend/dataset_acquisition/registry`` — real-dataset registry (T1-F/H).

Tracks the source / dataset / patient / recording / label / registry entities of the real
dataset. **No orphan records**: every entry must reference an audit head and a lineage node.
"""

from __future__ import annotations

from ..models.domain import AcquisitionRegistryRecord, EntityKind

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class RealDatasetRegistry:
    """In-memory catalog of real-dataset entities, keyed by entity id."""

    def __init__(self) -> None:
        self._records: dict[str, AcquisitionRegistryRecord] = {}
        self._version_sigs: dict[tuple, str] = {}

    def register(self, record: AcquisitionRegistryRecord) -> AcquisitionRegistryRecord:
        if not record.lineage_id:
            raise RegistryError(f"{record.entity_id!r} has no lineage node (orphans forbidden)")
        if not record.audit_state or record.audit_state == GENESIS:
            raise RegistryError(f"{record.entity_id!r} has no audit head (orphans forbidden)")
        key = (record.entity_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"{record.entity_id!r} v{record.version} already registered with different content")
        self._version_sigs[key] = sig
        self._records[record.entity_id] = record
        return record

    def get(self, entity_id: str) -> AcquisitionRegistryRecord:
        if entity_id not in self._records:
            raise KeyError(f"entity {entity_id!r} not in registry")
        return self._records[entity_id]

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._records

    def list_by_kind(self, kind: EntityKind) -> list:
        return sorted(eid for eid, r in self._records.items() if r.entity_kind == kind)

    def counts(self) -> dict:
        out = {k.value: 0 for k in EntityKind}
        for r in self._records.values():
            out[r.entity_kind.value] += 1
        return out

    def orphans(self) -> list:
        return sorted(eid for eid, r in self._records.items()
                      if not r.lineage_id or not r.audit_state or r.audit_state == GENESIS)

    def to_dict(self) -> dict:
        return {"n_records": len(self._records), "counts": self.counts(),
                "records": {eid: r.to_dict() for eid, r in sorted(self._records.items())}}


__all__ = ["RealDatasetRegistry", "RegistryError", "GENESIS"]
