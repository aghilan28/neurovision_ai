"""Application storage (P6-H) — local, in-process, compatible with the platform.

These are deliberately simple in-memory stores (plus one tiny content-addressed
on-disk byte store for uploaded files), matching the platform's existing in-memory
persistence model (the inherited G3 gap). **No cloud, no database, no distributed
systems** (all out of scope for P6). Each typed store keys immutable records by their
id and rejects a silent overwrite of the same id with *different* content.

The stores hold the *records*; the registry (P6-I) holds the discoverable index with
audit/lineage references. Credentials live in the dedicated :class:`CredentialStore`
and never appear in any other store, record, report, or hash.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from ml.provenance import full_sha256, hash_obj  # allowed: backend -> ml

from ..version import APPLICATION_STORAGE_VERSION

T = TypeVar("T")


class StorageError(RuntimeError):
    """Raised on a silent-overwrite attempt or a missing required record."""


class RecordStore(Generic[T]):
    """An append/replace-by-content store keyed by a string id.

    Re-putting the same id with an identical content signature is idempotent;
    re-putting it with a *different* signature is rejected (silent overwrite
    forbidden), unless ``allow_update`` records the change as a new content version.
    """

    def __init__(self, name: str, key_fn: Callable[[T], str], sig_fn: Callable[[T], str]):
        self._name = name
        self._key_fn = key_fn
        self._sig_fn = sig_fn
        self._records: dict[str, T] = {}
        self._sigs: dict[str, str] = {}

    def put(self, record: T, *, allow_update: bool = False) -> T:
        key = self._key_fn(record)
        sig = self._sig_fn(record)
        if key in self._sigs and self._sigs[key] != sig and not allow_update:
            raise StorageError(
                f"{self._name} {key!r} already stored with different content "
                "(silent overwrite forbidden)")
        self._records[key] = record
        self._sigs[key] = sig
        return record

    def get(self, key: str) -> T:
        if key not in self._records:
            raise StorageError(f"{self._name} {key!r} not found")
        return self._records[key]

    def find(self, key: str) -> Optional[T]:
        return self._records.get(key)

    def exists(self, key: str) -> bool:
        return key in self._records

    def list_ids(self) -> list[str]:
        return sorted(self._records)

    def values(self) -> list[T]:
        return [self._records[k] for k in sorted(self._records)]

    def __len__(self) -> int:
        return len(self._records)


@dataclass(frozen=True)
class CredentialRecord:
    """A stored credential (secret). Never serialized into any report or hash id."""

    user_id: str
    salt_hex: str
    hash_hex: str
    iterations: int
    algorithm: str = "pbkdf2_hmac_sha256"


class CredentialStore:
    """A private store for password credentials, separate from every other store."""

    def __init__(self) -> None:
        self._creds: dict[str, CredentialRecord] = {}

    def put(self, record: CredentialRecord) -> CredentialRecord:
        self._creds[record.user_id] = record
        return record

    def get(self, user_id: str) -> Optional[CredentialRecord]:
        return self._creds.get(user_id)

    def exists(self, user_id: str) -> bool:
        return user_id in self._creds

    def __len__(self) -> int:
        return len(self._creds)


class UploadByteStore:
    """A tiny content-addressed on-disk store for uploaded raw EEG bytes.

    Keeps the application's "received file" separate from the P1 ``LocalEEGStore``
    (which content-addresses the *ingested asset*). The reference returned is a path
    under ``root``; the same bytes always hash to the same content fingerprint.
    """

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def put_bytes(self, data: bytes, *, suffix: str = ".bin") -> tuple[str, str, int]:
        """Persist ``data`` content-addressed; return (reference, fingerprint, size)."""
        fingerprint = full_sha256(data)
        name = f"{fingerprint}{suffix}"
        path = os.path.join(self.root, name)
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(data)
        return path, fingerprint, len(data)

    def read_bytes(self, reference: str) -> bytes:
        with open(reference, "rb") as fh:
            return fh.read()

    def exists(self, reference: str) -> bool:
        return os.path.exists(reference)

    @staticmethod
    def fingerprint_of(data: bytes) -> str:
        return full_sha256(data)


# --- typed store factories (one per application entity) ----------------------
def _versioned_sig(record) -> str:
    return hash_obj({"id": getattr(record, "state_signature", lambda: "")(),
                     "v": record.version.version})


def make_user_store() -> RecordStore:
    # users are updated in place (new version); allow_update used by the service.
    return RecordStore("user", key_fn=lambda r: r.user_id,
                       sig_fn=lambda r: hash_obj({"s": r.state_signature(), "v": r.version.version}))


def make_session_store() -> RecordStore:
    return RecordStore("session", key_fn=lambda r: r.session_id,
                       sig_fn=lambda r: hash_obj({"s": r.state_signature(), "v": r.version.version}))


def make_upload_store() -> RecordStore:
    return RecordStore("upload", key_fn=lambda r: r.upload_id,
                       sig_fn=lambda r: hash_obj(r.to_dict()))


def make_workflow_store() -> RecordStore:
    return RecordStore("workflow", key_fn=lambda r: r.workflow_id,
                       sig_fn=lambda r: r.state_signature())


def make_analysis_store() -> RecordStore:
    return RecordStore("analysis", key_fn=lambda r: r.analysis_id,
                       sig_fn=lambda r: hash_obj(r.to_dict()))


def make_request_store() -> RecordStore:
    return RecordStore("request", key_fn=lambda r: r.request_id,
                       sig_fn=lambda r: hash_obj(r.to_dict()))


def make_response_store() -> RecordStore:
    return RecordStore("response", key_fn=lambda r: r.response_id,
                       sig_fn=lambda r: hash_obj(r.to_dict()))


STORAGE_VERSION = APPLICATION_STORAGE_VERSION

__all__ = [
    "StorageError", "RecordStore", "CredentialRecord", "CredentialStore", "UploadByteStore",
    "make_user_store", "make_session_store", "make_upload_store", "make_workflow_store",
    "make_analysis_store", "make_request_store", "make_response_store", "STORAGE_VERSION",
]
