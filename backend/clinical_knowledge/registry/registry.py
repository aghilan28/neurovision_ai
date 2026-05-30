"""The knowledge registry: versioned snapshots of the knowledge base."""

from __future__ import annotations

from ..version import KNOWLEDGE_REGISTRY_VERSION
from ..models.domain import KnowledgeRegistryRecord


class KnowledgeRegistry:
    """Versioned snapshots of the knowledge base keyed by ``version``.

    Each governed mutation registers a new snapshot version; re-registering the
    *same* version with different content is a forbidden silent overwrite.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, KnowledgeRegistryRecord] = {}
        self._version_sigs: dict[str, str] = {}
        self._latest: KnowledgeRegistryRecord | None = None

    def register(self, record: KnowledgeRegistryRecord) -> KnowledgeRegistryRecord:
        sig = record.content_signature()
        if record.version in self._version_sigs and self._version_sigs[record.version] != sig:
            raise ValueError(
                f"knowledge version {record.version} already registered with different content "
                "(silent overwrite forbidden)")
        self._version_sigs[record.version] = sig
        self._snapshots[record.version] = record
        self._latest = record
        return record

    def latest(self) -> KnowledgeRegistryRecord:
        if self._latest is None:
            raise KeyError("knowledge registry is empty")
        return self._latest

    def get(self, version: str) -> KnowledgeRegistryRecord:
        if version not in self._snapshots:
            raise KeyError(f"knowledge version {version!r} not in registry")
        return self._snapshots[version]

    def list_versions(self) -> list[str]:
        return sorted(self._snapshots)

    def to_dict(self) -> dict:
        return {"knowledge_registry_version": KNOWLEDGE_REGISTRY_VERSION,
                "n_snapshots": len(self._snapshots),
                "latest": self._latest.to_dict() if self._latest else None,
                "snapshots": {v: r.to_dict() for v, r in sorted(self._snapshots.items())}}
