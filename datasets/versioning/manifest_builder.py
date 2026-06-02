"""Manifest construction from validated records.

Builds a deterministic :class:`~datasets.schemas.manifest.DatasetManifest` from a
collection of validated records (or registry entries). The manifest's
``content_fingerprint`` is order-independent, so two manifests with the same
membership fingerprint identically regardless of how they were assembled.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from datasets import DATA_FOUNDATION_VERSION
from datasets.schemas.manifest import DatasetManifest, ManifestEntry


class _RecordLike(Protocol):
    """Minimal interface needed to build a manifest entry."""

    file_id: str
    content_sha256: str
    patient_id: str
    recording_id: str


def _to_entry(record: object) -> ManifestEntry:
    """Accept either a RegisteredRecord-like or a ValidatedEegRecord-like object."""
    # ValidatedEegRecord exposes content via raw_file / session.
    raw_file = getattr(record, "raw_file", None)
    if raw_file is not None:  # ValidatedEegRecord
        return ManifestEntry(
            file_id=record.file_id,  # type: ignore[attr-defined]
            content_sha256=raw_file.content_sha256,
            patient_id=record.patient_id,  # type: ignore[attr-defined]
            recording_id=record.session.recording_id,  # type: ignore[attr-defined]
        )
    # RegisteredRecord-like
    return ManifestEntry(
        file_id=record.file_id,  # type: ignore[attr-defined]
        content_sha256=record.content_sha256,  # type: ignore[attr-defined]
        patient_id=record.patient_id,  # type: ignore[attr-defined]
        recording_id=record.recording_id,  # type: ignore[attr-defined]
    )


def build_manifest(
    dataset_id: str,
    version: str,
    records: Iterable[object],
    *,
    description: str = "",
    created_at: str | None = None,
    data_foundation_version: str = DATA_FOUNDATION_VERSION,
) -> DatasetManifest:
    """Build a dataset manifest from validated/registered records.

    Entries are de-duplicated by ``file_id`` (the same content is listed once) and
    stored sorted by ``(content_sha256, file_id)`` for a stable, reproducible file.
    """
    by_file: dict[str, ManifestEntry] = {}
    for record in records:
        entry = _to_entry(record)
        by_file[entry.file_id] = entry

    ordered = tuple(
        sorted(by_file.values(), key=lambda e: (e.content_sha256, e.file_id))
    )
    return DatasetManifest(
        dataset_id=dataset_id,
        version=version,
        entries=ordered,
        data_foundation_version=data_foundation_version,
        description=description,
        created_at=created_at,
    )
