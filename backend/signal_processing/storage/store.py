"""Local, content-addressed storage for the *processed* (clean) signal (P2).

Persists the cleaned signal bytes (deterministic, quantized C-order float64) plus a
small JSON manifest, returning a ``ProcessedEEGStorageRecord`` with a checksum +
fingerprint and an integrity ``verify``. This is a separate store from the P1 raw
store — the raw EEG is never written to or modified. No cloud/S3/database/deployment.
"""

from __future__ import annotations

import os

import numpy as np

from ml.provenance import content_id, full_sha256, write_json  # allowed: backend -> ml

from ..models.domain import ProcessedEEGStorageRecord
from ..preprocessing.loader import serialize_signal, array_fingerprint
from ..version import DETERMINISTIC_EPOCH


class ProcessedSignalStore:
    """Filesystem store for processed signal bytes rooted at ``root_dir``."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def put(self, data: np.ndarray, *, sfreq: float, channel_labels: tuple[str, ...],
            lineage_refs: tuple[str, ...] = (),
            created_at: str = DETERMINISTIC_EPOCH) -> ProcessedEEGStorageRecord:
        """Persist the processed ``data`` and return its storage record."""
        payload = serialize_signal(data)
        checksum = full_sha256(payload)
        fingerprint = array_fingerprint(data)
        rel_dir = fingerprint
        rel_path = os.path.join(rel_dir, "processed.f64")
        dest = os.path.join(self.root_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.exists(dest):
            with open(dest, "wb") as fh:
                fh.write(payload)
        # deterministic sidecar manifest (shape/rate/labels)
        write_json(os.path.join(self.root_dir, rel_dir, "manifest.json"), {
            "shape": list(data.shape), "sfreq": round(float(sfreq), 6),
            "channel_labels": list(channel_labels), "dtype": "float64",
            "content_fingerprint": fingerprint})

        storage_id = content_id("signal-storage", {
            "checksum_sha256": checksum, "n_bytes": len(payload)})
        version = content_id("signal-storage-ver", {
            "storage_id": storage_id, "checksum_sha256": checksum,
            "content_fingerprint": fingerprint, "n_bytes": len(payload)})
        return ProcessedEEGStorageRecord(
            storage_id=storage_id, processed_file_reference=rel_path.replace(os.sep, "/"),
            checksum_sha256=checksum, content_fingerprint=fingerprint, n_bytes=len(payload),
            version=version, created_at=created_at, lineage_refs=tuple(lineage_refs))

    def abs_path(self, record: ProcessedEEGStorageRecord) -> str:
        return os.path.join(self.root_dir, record.processed_file_reference.replace("/", os.sep))

    def exists(self, record: ProcessedEEGStorageRecord) -> bool:
        return os.path.exists(self.abs_path(record))

    def read_bytes(self, record: ProcessedEEGStorageRecord) -> bytes:
        with open(self.abs_path(record), "rb") as fh:
            return fh.read()

    def verify(self, record: ProcessedEEGStorageRecord) -> bool:
        """True iff the stored processed bytes still match the recorded checksum + size."""
        try:
            data = self.read_bytes(record)
        except OSError:
            return False
        return full_sha256(data) == record.checksum_sha256 and len(data) == record.n_bytes
