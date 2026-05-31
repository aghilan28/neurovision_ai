"""Durable, content-addressed object storage engine (DRP4-C).

A deterministic, durable key/value store backed by the local filesystem. Objects are
serialized as **canonical JSON** (sorted keys, compact separators) so the same object always
serializes to the same bytes; each write produces a :class:`StorageRecord` carrying a sha256
**checksum** (over the on-disk bytes, for tamper detection) and a content **fingerprint**
(over the object, for reproducibility). Reads verify the checksum.

Durable + restart-recoverable: objects live as files under ``<root>/<namespace>/<key>.json``,
so a fresh engine pointed at the same root after a cold restart reads exactly the same state.
No business logic — this is storage only.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import StorageNamespace, StorageRecord
from ..version import DETERMINISTIC_EPOCH


class StorageError(RuntimeError):
    """Raised on a storage integrity failure (missing object or checksum mismatch)."""


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_key(key: str) -> str:
    # keep keys filesystem-safe + collision-free (content ids already are; be defensive)
    return key.replace("/", "_").replace("\\", "_")


class StorageEngine:
    """Filesystem-backed, content-addressed, tamper-evident object store."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    # --- paths ----------------------------------------------------------------
    def _ns_dir(self, namespace: str) -> str:
        d = os.path.join(self.root, namespace)
        os.makedirs(d, exist_ok=True)
        return d

    def _path(self, namespace: str, key: str) -> str:
        return os.path.join(self._ns_dir(namespace), f"{_safe_key(key)}.json")

    def uri(self, namespace: str, key: str) -> str:
        return f"file://{self._path(namespace, key)}"

    # --- write / read ---------------------------------------------------------
    def put(self, namespace: str, key: str, obj: Any, *,
            created_at: str = DETERMINISTIC_EPOCH) -> StorageRecord:
        ns = namespace.value if isinstance(namespace, StorageNamespace) else str(namespace)
        data = _canonical_bytes(obj)
        path = self._path(ns, key)
        # atomic-ish write (write temp then replace) so a crash never leaves a half file
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
        checksum = _checksum(data)
        fingerprint = hash_obj(obj)
        storage_id = "storage+" + hash_obj({"namespace": ns, "key": key, "fingerprint": fingerprint})
        return StorageRecord(
            storage_id=storage_id, namespace=ns, key=key, checksum=checksum, fingerprint=fingerprint,
            size_bytes=len(data), uri=self.uri(ns, key), created_at=created_at)

    def exists(self, namespace, key: str) -> bool:
        ns = namespace.value if isinstance(namespace, StorageNamespace) else str(namespace)
        return os.path.isfile(self._path(ns, key))

    def get(self, namespace, key: str, *, expected_checksum: str | None = None) -> Any:
        ns = namespace.value if isinstance(namespace, StorageNamespace) else str(namespace)
        path = self._path(ns, key)
        if not os.path.isfile(path):
            raise StorageError(f"missing object {ns}/{key}")
        with open(path, "rb") as fh:
            data = fh.read()
        if expected_checksum is not None and _checksum(data) != expected_checksum:
            raise StorageError(f"checksum mismatch for {ns}/{key} (tamper or corruption)")
        return json.loads(data.decode("utf-8"))

    def verify(self, record: StorageRecord) -> bool:
        """True iff the on-disk object still matches the record's checksum + fingerprint."""
        ns, key = record.namespace, record.key
        path = self._path(ns, key)
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as fh:
            data = fh.read()
        if _checksum(data) != record.checksum:
            return False
        return hash_obj(json.loads(data.decode("utf-8"))) == record.fingerprint

    def list_keys(self, namespace) -> list[str]:
        ns = namespace.value if isinstance(namespace, StorageNamespace) else str(namespace)
        d = os.path.join(self.root, ns)
        if not os.path.isdir(d):
            return []
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


__all__ = ["StorageEngine", "StorageError"]
