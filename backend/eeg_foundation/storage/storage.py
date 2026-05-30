"""EEG storage abstraction (Productization P1).

A repository-compatible **local** storage abstraction. It stores a real EEG file *by
reference* (the platform never relocates clinical raw data implicitly) and records the
integrity fields needed to trace and verify it: a sha256 checksum, a content
fingerprint, a content-addressed storage id, the file size, and a creation timestamp.

Optionally a content-addressed local copy can be made under a given ``root`` (still
local; no cloud/S3/deployment — explicitly out of scope). Deterministic: the same
bytes always yield the same checksum, fingerprint, and storage id.
"""

from __future__ import annotations

import hashlib
import os
import shutil

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EEG_STORAGE_VERSION, DETERMINISTIC_EPOCH
from ..identity import mint_storage_id
from ..models.domain import EEGStorageRecord

_CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_for(checksum: str, size: int, fmt: str) -> str:
    return hash_obj({"checksum": checksum, "size": size, "format": fmt,
                     "storage_version": EEG_STORAGE_VERSION})


class LocalEEGStore:
    """Local, reference-based EEG store (optionally content-addressed copy under root)."""

    def __init__(self, root: str | None = None, *, copy: bool = False):
        self.root = root
        self.copy = copy and root is not None

    def store(self, path: str, *, fmt: str, created_at: str = DETERMINISTIC_EPOCH
              ) -> EEGStorageRecord:
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        size = os.path.getsize(path)
        checksum = sha256_file(path)
        fingerprint = fingerprint_for(checksum, size, fmt)
        storage_id = mint_storage_id(checksum)

        location = os.path.abspath(path)
        backend = "local-reference"
        if self.copy:
            os.makedirs(self.root, exist_ok=True)
            ext = os.path.splitext(path)[1]
            dest = os.path.join(self.root, f"{storage_id}{ext}")
            if not os.path.exists(dest):
                shutil.copy2(path, dest)
            location = os.path.abspath(dest)
            backend = "local-copy"

        return EEGStorageRecord(
            storage_id=storage_id, backend=backend, location=location,
            checksum_sha256=checksum, fingerprint=fingerprint, file_size_bytes=size,
            created_at=created_at)
