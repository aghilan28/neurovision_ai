"""Contract: *Dataset Manifest*.

A :class:`DatasetManifest` is the deterministic, content-addressed listing of
exactly which records (by content checksum) constitute a dataset at a point in
time. Its :pyattr:`content_fingerprint` is a SHA-256 over the canonical, sorted
membership — so two manifests are identical *iff* they list the same content.
This is the mechanism that makes "no silent dataset modifications" detectable
(Project directive; AP-6/NR-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datasets._canonical import canonical_fingerprint


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One content-addressed member of a dataset manifest."""

    file_id: str
    content_sha256: str
    patient_id: str
    recording_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "content_sha256": self.content_sha256,
            "patient_id": self.patient_id,
            "recording_id": self.recording_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestEntry:
        return cls(
            file_id=data["file_id"],
            content_sha256=data["content_sha256"],
            patient_id=data["patient_id"],
            recording_id=data["recording_id"],
        )


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Deterministic, content-addressed membership listing for a dataset.

    Notes
    -----
    * Entries are *stored* in insertion order but **fingerprinted in sorted order**
      so the fingerprint is independent of insertion order (only content matters).
    * ``data_foundation_version`` participates in the fingerprint: a change to the
      foundation that could alter interpretation invalidates old fingerprints
      deliberately (reproducibility honesty, AP-6).
    """

    dataset_id: str
    version: str
    entries: tuple[ManifestEntry, ...]
    data_foundation_version: str
    description: str = ""
    created_at: str | None = None  # provenance only; excluded from fingerprint
    extra: dict[str, Any] = field(default_factory=dict)

    # --- derived, deterministic views ------------------------------------
    @property
    def record_count(self) -> int:
        return len(self.entries)

    @property
    def patient_ids(self) -> tuple[str, ...]:
        return tuple(sorted({e.patient_id for e in self.entries}))

    @property
    def patient_count(self) -> int:
        return len(self.patient_ids)

    def _fingerprint_payload(self) -> dict[str, Any]:
        """The canonical, order-independent payload that defines dataset *content*.

        Deliberately excludes the ``version`` label and volatile fields: the
        fingerprint identifies the *membership*, so two version labels with the
        same records share a fingerprint (which is how an accidental "no-op"
        re-version is detected). It includes ``data_foundation_version`` because a
        foundation change can alter interpretation and should invalidate old
        fingerprints honestly (AP-6).
        """
        sorted_entries = sorted(
            (e.to_dict() for e in self.entries),
            key=lambda d: (d["content_sha256"], d["file_id"]),
        )
        return {
            "dataset_id": self.dataset_id,
            "data_foundation_version": self.data_foundation_version,
            "entries": sorted_entries,
        }

    @property
    def content_fingerprint(self) -> str:
        """SHA-256 fingerprint of the dataset's content (excludes volatile fields)."""
        return canonical_fingerprint(self._fingerprint_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "data_foundation_version": self.data_foundation_version,
            "description": self.description,
            "created_at": self.created_at,
            "record_count": self.record_count,
            "patient_count": self.patient_count,
            "content_fingerprint": self.content_fingerprint,
            "entries": [e.to_dict() for e in self.entries],
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetManifest:
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            data_foundation_version=data["data_foundation_version"],
            description=data.get("description", ""),
            created_at=data.get("created_at"),
            entries=tuple(ManifestEntry.from_dict(e) for e in data.get("entries", [])),
            extra=dict(data.get("extra", {})),
        )
