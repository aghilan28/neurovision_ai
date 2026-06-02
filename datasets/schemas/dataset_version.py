"""Contract: *Dataset Version*.

A :class:`DatasetVersion` records an immutable, fingerprinted snapshot of a
dataset and its relationship to a parent version. Versions form an append-only
chain: each new version names its ``parent_version`` and the
``manifest_fingerprint`` it certifies, plus a human-readable change summary. This
is how the platform guarantees **no silent dataset modifications** and supports
dataset audits and reproducibility tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    """An immutable, fingerprinted dataset snapshot in the version chain."""

    dataset_id: str
    version: str
    manifest_fingerprint: str
    data_foundation_version: str
    parent_version: str | None = None
    record_count: int = 0
    patient_count: int = 0
    change_summary: str = ""
    created_at: str | None = None  # provenance only
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "manifest_fingerprint": self.manifest_fingerprint,
            "data_foundation_version": self.data_foundation_version,
            "parent_version": self.parent_version,
            "record_count": self.record_count,
            "patient_count": self.patient_count,
            "change_summary": self.change_summary,
            "created_at": self.created_at,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetVersion:
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            manifest_fingerprint=data["manifest_fingerprint"],
            data_foundation_version=data["data_foundation_version"],
            parent_version=data.get("parent_version"),
            record_count=int(data.get("record_count", 0)),
            patient_count=int(data.get("patient_count", 0)),
            change_summary=data.get("change_summary", ""),
            created_at=data.get("created_at"),
            extra=dict(data.get("extra", {})),
        )
