"""Typed durable repositories (DRP4-D).

A thin, reusable, deterministic repository over the storage engine — one per artifact kind
(datasets, models, training runs, benchmarks, inference, serving, audit, lineage). It stores
the artifacts' already-serialized ``to_dict()`` projections (no duplicated business logic),
keyed by their own id, and produces a :class:`RepositoryRecord` manifest. Reading back is a
pure load + checksum-verify.
"""

from __future__ import annotations

from typing import Mapping

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import RepositoryKind, RepositoryRecord, StorageNamespace
from ..storage import StorageEngine


class RepositoryError(RuntimeError):
    """Raised on a repository read/write integrity failure."""


class Repository:
    """A durable, content-addressed repository for one artifact kind."""

    def __init__(self, engine: StorageEngine, kind: RepositoryKind):
        self.engine = engine
        self.kind = kind
        self._checksums: dict[str, str] = {}

    @property
    def _namespace(self) -> str:
        return f"{StorageNamespace.REPOSITORY.value}.{self.kind.value}"

    def save(self, record_id: str, record_dict: Mapping) -> str:
        """Persist one record under its id; return the storage checksum."""
        if not record_id:
            raise RepositoryError(f"{self.kind.value} record has no id")
        sr = self.engine.put(self._namespace, record_id, dict(record_dict))
        self._checksums[record_id] = sr.checksum
        return sr.checksum

    def save_all(self, records: Mapping[str, Mapping]) -> RepositoryRecord:
        """Persist many records; return the repository manifest."""
        for rid, rec in records.items():
            self.save(rid, rec)
        return self.manifest()

    def load(self, record_id: str) -> dict:
        return self.engine.get(self._namespace, record_id,
                               expected_checksum=self._checksums.get(record_id))

    def load_all(self) -> dict:
        return {rid: self.engine.get(self._namespace, rid) for rid in self.list_ids()}

    def exists(self, record_id: str) -> bool:
        return self.engine.exists(self._namespace, record_id)

    def list_ids(self) -> list[str]:
        return self.engine.list_keys(self._namespace)

    def manifest(self) -> RepositoryRecord:
        ids = self.list_ids()
        fingerprint = hash_obj({"kind": self.kind.value, "record_ids": ids})
        storage_id = "storage+" + hash_obj({"namespace": self._namespace, "manifest": fingerprint})
        return RepositoryRecord(repository_kind=self.kind.value, n_records=len(ids),
                                record_ids=tuple(ids), fingerprint=fingerprint, storage_id=storage_id)


__all__ = ["Repository", "RepositoryError"]
