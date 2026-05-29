"""Contract: *Validated EEG Record*.

A :class:`ValidatedEegRecord` is the composite, lifecycle-complete artifact for a
single file: the raw file, its canonical metadata, its validation report, its
quality report, and its derived patient/session. It is the unit a dataset is
built from and the anchor for that record's lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets.schemas.enums import RecordStatus
from datasets.schemas.metadata_record import MetadataRecord
from datasets.schemas.patient_record import PatientRecord
from datasets.schemas.raw_eeg_file import RawEegFile
from datasets.schemas.recording_session import RecordingSession
from datasets.schemas.reports import QualityReport, ValidationReport


@dataclass(frozen=True, slots=True)
class ValidatedEegRecord:
    """A fully-ingested, validated EEG record (the lifecycle's central artifact)."""

    raw_file: RawEegFile
    metadata: MetadataRecord
    patient: PatientRecord
    session: RecordingSession
    validation: ValidationReport
    quality: QualityReport
    status: RecordStatus
    lineage_id: str | None = None

    @property
    def file_id(self) -> str:
        return self.raw_file.file_id

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id

    @property
    def is_acceptable(self) -> bool:
        """True when validation did not fail (no ERROR findings)."""
        return self.validation.status.is_acceptable

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_file": self.raw_file.to_dict(),
            "metadata": self.metadata.to_dict(),
            "patient": self.patient.to_dict(),
            "session": self.session.to_dict(),
            "validation": self.validation.to_dict(),
            "quality": self.quality.to_dict(),
            "status": self.status.value,
            "lineage_id": self.lineage_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidatedEegRecord:
        return cls(
            raw_file=RawEegFile.from_dict(data["raw_file"]),
            metadata=MetadataRecord.from_dict(data["metadata"]),
            patient=PatientRecord.from_dict(data["patient"]),
            session=RecordingSession.from_dict(data["session"]),
            validation=ValidationReport.from_dict(data["validation"]),
            quality=QualityReport.from_dict(data["quality"]),
            status=RecordStatus(data["status"]),
            lineage_id=data.get("lineage_id"),
        )
