"""``backend/dataset_acquisition/storage`` — Local Dataset Management (T1-B).

Tracks the **actual** local state of real datasets on disk:

* ``DatasetStorageManager`` — resolves per-source local roots under a single data root
  (default ``data/real``, overridable via ``NV_DATASET_ROOT``) and lists/reads real files.
* ``DatasetLocationRegistry`` — maps each source to its resolved local root.
* ``DatasetVerificationManager`` — verifies a file's integrity (existence, non-emptiness,
  and checksum match when an expected checksum is known) -> a ``LocalFileRecord`` state.
* ``DatasetAvailabilityTracker`` — folds per-file states + expected/missing into a dataset
  ``AvailabilityRecord`` with the closed availability vocabulary.

No business logic, no model training — just the real disk state. Checksums reuse the
platform's ``sha256_of_file`` (no parallel hashing).
"""

from __future__ import annotations

import os

from ml.provenance import sha256_of_file  # allowed: backend -> ml

from ..models.domain import (
    AvailabilityRecord, AvailabilityState, DatasetSource, LocalFileRecord,
)

_DEFAULT_DATA_ROOT = "data/real"


def default_data_root() -> str:
    """The base directory that holds acquired corpora (env-overridable, gitignored)."""
    return os.environ.get("NV_DATASET_ROOT", _DEFAULT_DATA_ROOT)


class DatasetStorageManager:
    """Resolves per-source local roots and reads the real files on disk."""

    def __init__(self, data_root: str | None = None) -> None:
        self.data_root = os.path.abspath(data_root or default_data_root())

    def source_root(self, source: DatasetSource) -> str:
        return os.path.join(self.data_root, source.value)

    def ensure_root(self, source: DatasetSource) -> str:
        root = self.source_root(source)
        os.makedirs(root, exist_ok=True)
        return root

    def abspath(self, source: DatasetSource, relative_path: str) -> str:
        return os.path.join(self.source_root(source), relative_path)

    def exists(self, source: DatasetSource, relative_path: str) -> bool:
        return os.path.isfile(self.abspath(source, relative_path))

    def list_files(self, source: DatasetSource, *, suffixes: tuple = ()) -> list[str]:
        """Return real files under the source root (repo-relative to that root), sorted."""
        root = self.source_root(source)
        if not os.path.isdir(root):
            return []
        out: list[str] = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if suffixes and not name.lower().endswith(suffixes):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                out.append(rel.replace(os.sep, "/"))
        return sorted(out)

    def file_size(self, source: DatasetSource, relative_path: str) -> int:
        return os.path.getsize(self.abspath(source, relative_path))


class DatasetLocationRegistry:
    """In-memory map of source -> resolved local root (the Dataset Location Registry)."""

    def __init__(self) -> None:
        self._locations: dict[str, str] = {}

    def set_location(self, source: DatasetSource, root: str) -> None:
        self._locations[source.value] = os.path.abspath(root)

    def location(self, source: DatasetSource) -> str | None:
        return self._locations.get(source.value)

    def to_dict(self) -> dict:
        return dict(sorted(self._locations.items()))


class DatasetVerificationManager:
    """Verifies the integrity of real files on disk (Dataset Verification Manager)."""

    def __init__(self, storage: DatasetStorageManager) -> None:
        self.storage = storage

    def verify_file(self, source: DatasetSource, relative_path: str, *,
                    expected_checksum: str | None = None,
                    expected_size: int | None = None) -> LocalFileRecord:
        abspath = self.storage.abspath(source, relative_path)
        if not os.path.isfile(abspath):
            return LocalFileRecord(relative_path=relative_path, absolute_path=abspath,
                                   size_bytes=0, checksum_sha256="",
                                   state=AvailabilityState.UNAVAILABLE)
        size = os.path.getsize(abspath)
        if size == 0:
            return LocalFileRecord(relative_path=relative_path, absolute_path=abspath,
                                   size_bytes=0, checksum_sha256="",
                                   state=AvailabilityState.CORRUPTED)
        checksum = sha256_of_file(abspath)
        # An explicit mismatch (checksum or truncated size) -> corrupted.
        if expected_checksum and checksum != expected_checksum:
            return LocalFileRecord(relative_path=relative_path, absolute_path=abspath,
                                   size_bytes=size, checksum_sha256=checksum,
                                   state=AvailabilityState.CORRUPTED)
        if expected_size is not None and size < expected_size:
            return LocalFileRecord(relative_path=relative_path, absolute_path=abspath,
                                   size_bytes=size, checksum_sha256=checksum,
                                   state=AvailabilityState.PARTIALLY_DOWNLOADED)
        # Present, non-empty, and (if known) matches -> verified.
        state = (AvailabilityState.VERIFIED if expected_checksum
                 else AvailabilityState.VERIFIED)
        return LocalFileRecord(relative_path=relative_path, absolute_path=abspath,
                               size_bytes=size, checksum_sha256=checksum, state=state)


class DatasetAvailabilityTracker:
    """Folds per-file verification into a dataset-level availability state (Tracker)."""

    def __init__(self, storage: DatasetStorageManager,
                 verifier: DatasetVerificationManager | None = None) -> None:
        self.storage = storage
        self.verifier = verifier or DatasetVerificationManager(storage)

    def track(self, source: DatasetSource, *, expected_files: tuple = (),
              discovered_files: tuple = ()) -> AvailabilityRecord:
        root = self.storage.source_root(source)
        files = tuple(discovered_files) or tuple(self.storage.list_files(source))
        records = [self.verifier.verify_file(source, rel) for rel in files]
        n_verified = sum(1 for r in records if r.state == AvailabilityState.VERIFIED)
        corrupted = tuple(r.relative_path for r in records
                          if r.state == AvailabilityState.CORRUPTED)
        total_bytes = sum(r.size_bytes for r in records)
        present = {r.relative_path for r in records}
        missing = tuple(sorted(set(expected_files) - present)) if expected_files else ()

        if not os.path.isdir(root) or not records:
            state = AvailabilityState.UNAVAILABLE
        elif corrupted:
            state = AvailabilityState.CORRUPTED
        elif missing:
            state = AvailabilityState.PARTIALLY_DOWNLOADED
        elif n_verified == len(records) and records:
            state = AvailabilityState.VERIFIED
        else:
            state = AvailabilityState.DOWNLOADED

        return AvailabilityRecord(
            source=source, local_root=root, state=state, n_files=len(records),
            n_verified=n_verified, total_bytes=total_bytes,
            expected_files=tuple(expected_files), missing_files=missing,
            corrupted_files=corrupted)


__all__ = [
    "default_data_root", "DatasetStorageManager", "DatasetLocationRegistry",
    "DatasetVerificationManager", "DatasetAvailabilityTracker",
]
