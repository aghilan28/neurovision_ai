"""Local, repository-compatible EEG storage abstraction (P1-E).

Stores the *raw* EEG file by reference + integrity metadata. This is deliberately a
local filesystem store — **no cloud, no S3, no database, no deployment
infrastructure** (those are forbidden in this phase). The goal is correct
architecture: a content-addressed store with checksums and fingerprints that a
future durable backend can implement behind the same ``EEGStorageRecord`` contract.

Content addressing: files are placed under ``<root>/<content_fingerprint>/<name>``
where ``content_fingerprint`` is the leading 16 hex of the file's sha256. Identical
bytes therefore map to the same location (idempotent), and ``verify`` re-reads the
stored bytes to detect any silent modification (artifact integrity, NR-10).
"""

from __future__ import annotations

import os
import shutil

from ml.provenance import content_id, full_sha256  # allowed: backend -> ml

from ..models.domain import EEGFormat, EEGStorageRecord
from ..version import DETERMINISTIC_EPOCH


def fingerprint_of_checksum(checksum_sha256: str) -> str:
    """The short (16-hex) content fingerprint derived from a full sha256."""
    return checksum_sha256[:16]


def _safe_name(name: str) -> str:
    base = os.path.basename(name or "").strip()
    return base or "eeg_recording"


class LocalEEGStore:
    """A filesystem-backed EEG blob store rooted at ``root_dir``."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def put(self, src_path: str, *, eeg_format: EEGFormat,
            lineage_refs: tuple[str, ...] = (), created_at: str = DETERMINISTIC_EPOCH) -> EEGStorageRecord:
        """Copy ``src_path`` into the store and return its ``EEGStorageRecord``."""
        with open(src_path, "rb") as fh:
            data = fh.read()
        checksum = full_sha256(data)
        size = len(data)
        fingerprint = fingerprint_of_checksum(checksum)

        rel_dir = fingerprint
        rel_path = os.path.join(rel_dir, _safe_name(src_path))
        dest = os.path.join(self.root_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.exists(dest):
            shutil.copyfile(src_path, dest)

        storage_id = content_id("eeg-storage", {
            "checksum_sha256": checksum, "file_size_bytes": size, "eeg_format": eeg_format.value})
        version = content_id("eeg-storage-ver", {
            "storage_id": storage_id, "checksum_sha256": checksum,
            "content_fingerprint": fingerprint, "file_size_bytes": size,
            "eeg_format": eeg_format.value})

        return EEGStorageRecord(
            storage_id=storage_id,
            raw_file_reference=rel_path.replace(os.sep, "/"),
            eeg_format=eeg_format,
            checksum_sha256=checksum,
            content_fingerprint=fingerprint,
            file_size_bytes=size,
            version=version,
            created_at=created_at,
            lineage_refs=tuple(lineage_refs),
        )

    def abs_path(self, record: EEGStorageRecord) -> str:
        return os.path.join(self.root_dir, record.raw_file_reference.replace("/", os.sep))

    def exists(self, record: EEGStorageRecord) -> bool:
        return os.path.exists(self.abs_path(record))

    def read_bytes(self, record: EEGStorageRecord) -> bytes:
        with open(self.abs_path(record), "rb") as fh:
            return fh.read()

    def verify(self, record: EEGStorageRecord) -> bool:
        """True iff the stored bytes still match the recorded checksum + size."""
        try:
            data = self.read_bytes(record)
        except OSError:
            return False
        return full_sha256(data) == record.checksum_sha256 and len(data) == record.file_size_bytes
