"""Contract: *Dataset Entry*.

A :class:`DatasetEntry` is the membership of one validated record in one dataset.
It binds ``dataset_id`` + ``file_id`` + ``patient_id`` together with the content
checksum so that a dataset's membership is itself content-addressed and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets.schemas.enums import QualityState, RecordStatus, ValidationStatus


@dataclass(frozen=True, slots=True)
class DatasetEntry:
    """One record's membership in a dataset."""

    dataset_id: str
    file_id: str
    patient_id: str
    recording_id: str
    content_sha256: str
    validation_status: ValidationStatus
    quality_state: QualityState
    status: RecordStatus = RecordStatus.REGISTERED
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "file_id": self.file_id,
            "patient_id": self.patient_id,
            "recording_id": self.recording_id,
            "content_sha256": self.content_sha256,
            "validation_status": self.validation_status.value,
            "quality_state": self.quality_state.value,
            "status": self.status.value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetEntry:
        return cls(
            dataset_id=data["dataset_id"],
            file_id=data["file_id"],
            patient_id=data["patient_id"],
            recording_id=data["recording_id"],
            content_sha256=data["content_sha256"],
            validation_status=ValidationStatus(data["validation_status"]),
            quality_state=QualityState(data["quality_state"]),
            status=RecordStatus(data.get("status", RecordStatus.REGISTERED.value)),
            note=data.get("note"),
        )
