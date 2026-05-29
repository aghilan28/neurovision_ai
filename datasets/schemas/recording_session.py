"""Contract: *Recording Session*.

A recording session is one continuous acquisition — in EDF, one file. It links a
patient to a file and carries the temporal descriptors (start, duration). Keeping
this separate from the file and the metadata lets later versions model multi-file
or streaming sessions (V3) without reshaping the data contracts (AP-1, no rewrites).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RecordingSession:
    """One EEG recording session (one EDF file in V1)."""

    recording_id: str
    patient_id: str
    file_id: str
    start_date: str
    start_time: str
    duration_seconds: float
    start_datetime_iso: str | None = None
    equipment: str | None = None
    admin_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recording_id": self.recording_id,
            "patient_id": self.patient_id,
            "file_id": self.file_id,
            "start_date": self.start_date,
            "start_time": self.start_time,
            "duration_seconds": self.duration_seconds,
            "start_datetime_iso": self.start_datetime_iso,
            "equipment": self.equipment,
            "admin_code": self.admin_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordingSession:
        return cls(
            recording_id=data["recording_id"],
            patient_id=data["patient_id"],
            file_id=data["file_id"],
            start_date=data["start_date"],
            start_time=data["start_time"],
            duration_seconds=float(data["duration_seconds"]),
            start_datetime_iso=data.get("start_datetime_iso"),
            equipment=data.get("equipment"),
            admin_code=data.get("admin_code"),
        )
