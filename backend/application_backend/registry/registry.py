"""The application registry (P6-I) — one discoverable index of every entity.

Tracks users, sessions, uploads, requests, responses, workflows, analyses, and the API
contract. **No orphan records**: every entry must carry both an audit head and a
lineage node id (enforced at registration), so each registered entity is traceable and
auditable. Re-registering the same ``(entity_id, version)`` with different content is
rejected (silent overwrite forbidden). Mirrors the platform registry pattern (NR-6).
"""

from __future__ import annotations

from ..models.domain import BackendRegistryRecord, EntityKind
from ..version import APPLICATION_REGISTRY_VERSION

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class BackendRegistry:
    """In-memory application registry keyed by ``entity_id`` (scoped by kind)."""

    def __init__(self) -> None:
        self._records: dict[str, BackendRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: BackendRegistryRecord) -> BackendRegistryRecord:
        # --- no orphan records: require audit + lineage references ---
        if not record.lineage_id:
            raise RegistryError(
                f"{record.entity_kind.value} {record.entity_id!r} has no lineage node "
                "(orphan records forbidden)")
        if not record.audit_state or record.audit_state == GENESIS:
            raise RegistryError(
                f"{record.entity_kind.value} {record.entity_id!r} has no audit head "
                "(orphan records forbidden)")
        key = (record.entity_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"{record.entity_kind.value} {record.entity_id!r} version {record.version} "
                "already registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.entity_id] = record
        return record

    def get(self, entity_id: str) -> BackendRegistryRecord:
        if entity_id not in self._records:
            raise KeyError(f"entity {entity_id!r} not in registry")
        return self._records[entity_id]

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._records

    def list_ids(self) -> list[str]:
        return sorted(self._records)

    def list_by_kind(self, kind: EntityKind) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.entity_kind == kind)

    def by_user(self, user_id: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.user_id == user_id)

    def counts(self) -> dict:
        out = {k.value: 0 for k in EntityKind}
        for r in self._records.values():
            out[r.entity_kind.value] += 1
        return out

    def orphans(self) -> list[str]:
        """Any record missing an audit head or lineage id (must always be empty)."""
        return sorted(eid for eid, r in self._records.items()
                      if not r.lineage_id or not r.audit_state or r.audit_state == GENESIS)

    def to_dict(self) -> dict:
        return {
            "application_registry_version": APPLICATION_REGISTRY_VERSION,
            "n_records": len(self._records), "counts": self.counts(),
            "records": {eid: r.to_dict() for eid, r in sorted(self._records.items())},
        }


__all__ = ["BackendRegistry", "RegistryError"]
