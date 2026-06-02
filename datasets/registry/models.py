"""Registry record models.

Lightweight, serializable summaries the registries persist. These are *index*
entries — compact projections of the full artifacts — designed for discovery and
status tracking, not for carrying signal data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datasets.schemas.enums import DatasetStatus, QualityState, RecordStatus, ValidationStatus
from datasets.schemas.validated_record import ValidatedEegRecord


@dataclass(frozen=True, slots=True)
class RegisteredRecord:
    """An index entry for one ingested EEG record."""

    file_id: str
    content_sha256: str
    patient_id: str
    recording_id: str
    validation_status: ValidationStatus
    quality_state: QualityState
    status: RecordStatus
    lineage_id: str | None = None
    source_path: str | None = None
    dataset_ids: tuple[str, ...] = ()

    @classmethod
    def from_validated_record(cls, record: ValidatedEegRecord) -> RegisteredRecord:
        return cls(
            file_id=record.file_id,
            content_sha256=record.raw_file.content_sha256,
            patient_id=record.patient_id,
            recording_id=record.session.recording_id,
            validation_status=record.validation.status,
            quality_state=record.quality.state,
            status=record.status,
            lineage_id=record.lineage_id,
            source_path=record.raw_file.source_path,
        )

    def with_dataset(self, dataset_id: str) -> RegisteredRecord:
        merged = tuple(sorted(set(self.dataset_ids) | {dataset_id}))
        return RegisteredRecord(
            file_id=self.file_id,
            content_sha256=self.content_sha256,
            patient_id=self.patient_id,
            recording_id=self.recording_id,
            validation_status=self.validation_status,
            quality_state=self.quality_state,
            status=self.status,
            lineage_id=self.lineage_id,
            source_path=self.source_path,
            dataset_ids=merged,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "content_sha256": self.content_sha256,
            "patient_id": self.patient_id,
            "recording_id": self.recording_id,
            "validation_status": self.validation_status.value,
            "quality_state": self.quality_state.value,
            "status": self.status.value,
            "lineage_id": self.lineage_id,
            "source_path": self.source_path,
            "dataset_ids": list(self.dataset_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisteredRecord:
        return cls(
            file_id=data["file_id"],
            content_sha256=data["content_sha256"],
            patient_id=data["patient_id"],
            recording_id=data["recording_id"],
            validation_status=ValidationStatus(data["validation_status"]),
            quality_state=QualityState(data["quality_state"]),
            status=RecordStatus(data["status"]),
            lineage_id=data.get("lineage_id"),
            source_path=data.get("source_path"),
            dataset_ids=tuple(data.get("dataset_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class RegisteredDataset:
    """An index entry for a dataset (a versioned collection of records)."""

    dataset_id: str
    name: str
    owner: str
    source: str
    status: DatasetStatus = DatasetStatus.DRAFT
    current_version: str | None = None
    versions: tuple[str, ...] = ()
    validation_state: ValidationStatus = ValidationStatus.PASSED
    quality_state: QualityState = QualityState.UNKNOWN
    dependencies: tuple[str, ...] = ()
    lineage_ref: str | None = None
    description: str = ""
    record_count: int = 0
    patient_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "owner": self.owner,
            "source": self.source,
            "status": self.status.value,
            "current_version": self.current_version,
            "versions": list(self.versions),
            "validation_state": self.validation_state.value,
            "quality_state": self.quality_state.value,
            "dependencies": list(self.dependencies),
            "lineage_ref": self.lineage_ref,
            "description": self.description,
            "record_count": self.record_count,
            "patient_count": self.patient_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisteredDataset:
        return cls(
            dataset_id=data["dataset_id"],
            name=data["name"],
            owner=data["owner"],
            source=data["source"],
            status=DatasetStatus(data.get("status", DatasetStatus.DRAFT.value)),
            current_version=data.get("current_version"),
            versions=tuple(data.get("versions", ())),
            validation_state=ValidationStatus(
                data.get("validation_state", ValidationStatus.PASSED.value)
            ),
            quality_state=QualityState(data.get("quality_state", QualityState.UNKNOWN.value)),
            dependencies=tuple(data.get("dependencies", ())),
            lineage_ref=data.get("lineage_ref"),
            description=data.get("description", ""),
            record_count=int(data.get("record_count", 0)),
            patient_count=int(data.get("patient_count", 0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            extra=dict(data.get("extra", {})),
        )
