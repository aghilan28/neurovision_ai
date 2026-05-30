"""The temporal registry: governed, versioned, traceable temporal artifacts (V3-P2).

No temporal artifact may exist outside the registry. Re-registering the same id +
version with different content is a forbidden silent overwrite.
"""

from __future__ import annotations

from ..version import TEMPORAL_REGISTRY_VERSION
from ..models.domain import TemporalRegistryRecord


class TemporalRegistry:
    """In-memory registry keyed by ``artifact_id`` (latest record per artifact)."""

    def __init__(self) -> None:
        self._records: dict[str, TemporalRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: TemporalRegistryRecord) -> TemporalRegistryRecord:
        key = (record.artifact_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"temporal artifact {record.artifact_id} version {record.version} already "
                "registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.artifact_id] = record
        return record

    def get(self, artifact_id: str) -> TemporalRegistryRecord:
        if artifact_id not in self._records:
            raise KeyError(f"temporal artifact {artifact_id!r} not in registry")
        return self._records[artifact_id]

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._records

    def list_artifacts(self) -> list[str]:
        return sorted(self._records)

    def by_kind(self, artifact_kind: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.artifact_kind == artifact_kind)

    def to_dict(self) -> dict:
        return {"temporal_registry_version": TEMPORAL_REGISTRY_VERSION,
                "n_artifacts": len(self._records),
                "artifacts": {aid: r.to_dict() for aid, r in sorted(self._records.items())}}
