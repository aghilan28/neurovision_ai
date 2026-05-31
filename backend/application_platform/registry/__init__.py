"""``backend/application_platform/registry`` — product application registry (T3-H).

Tracks uploads / analyses / prediction requests + results / reports / workflow executions /
readiness assessments. **No orphan records**: every entry must reference an audit head and
a lineage node.
"""

from __future__ import annotations

from ..models.domain import ApplicationRegistryRecord, EntityKind

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class ApplicationRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ApplicationRegistryRecord] = {}
        self._sigs: dict[tuple, str] = {}

    def register(self, record: ApplicationRegistryRecord) -> ApplicationRegistryRecord:
        if not record.lineage_id:
            raise RegistryError(f"{record.entity_id!r} has no lineage node (orphans forbidden)")
        if not record.audit_state or record.audit_state == GENESIS:
            raise RegistryError(f"{record.entity_id!r} has no audit head (orphans forbidden)")
        key = (record.entity_id, record.version)
        sig = record.content_signature()
        if key in self._sigs and self._sigs[key] != sig:
            raise RegistryError(f"{record.entity_id!r} v{record.version} already registered "
                                "with different content")
        self._sigs[key] = sig
        self._records[record.entity_id] = record
        return record

    def get(self, entity_id: str) -> ApplicationRegistryRecord:
        if entity_id not in self._records:
            raise KeyError(f"entity {entity_id!r} not in registry")
        return self._records[entity_id]

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._records

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


__all__ = ["ApplicationRegistry", "RegistryError", "GENESIS"]
