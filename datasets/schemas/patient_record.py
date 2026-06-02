"""Contract: *Patient Record*.

Patient identity is the **load-bearing primitive for patient-disjoint validation**
(AP-2, NR-3). Every recording is anchored to exactly one patient; downstream
splitting guarantees a patient never spans partitions. This contract therefore
treats the patient identifier as authoritative and immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PatientRecord:
    """A de-identified patient and the recordings attributed to them.

    ``patient_id`` is deterministic (derived from the EDF+ patient code/field, or
    a content-derived fallback). ``raw_patient_field`` preserves the original
    header text for traceability. PII is intentionally *not* expanded here; only
    coarse, header-provided attributes are retained.
    """

    patient_id: str
    raw_patient_field: str
    sex: str | None = None  # "M" / "F" / "X" / None as encoded by EDF+
    birthdate_iso: str | None = None
    recording_ids: tuple[str, ...] = ()

    def with_recording(self, recording_id: str) -> PatientRecord:
        """Return a copy with ``recording_id`` added (deterministic, sorted, unique)."""
        merged = tuple(sorted(set(self.recording_ids) | {recording_id}))
        return PatientRecord(
            patient_id=self.patient_id,
            raw_patient_field=self.raw_patient_field,
            sex=self.sex,
            birthdate_iso=self.birthdate_iso,
            recording_ids=merged,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "raw_patient_field": self.raw_patient_field,
            "sex": self.sex,
            "birthdate_iso": self.birthdate_iso,
            "recording_ids": list(self.recording_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PatientRecord:
        return cls(
            patient_id=data["patient_id"],
            raw_patient_field=data["raw_patient_field"],
            sex=data.get("sex"),
            birthdate_iso=data.get("birthdate_iso"),
            recording_ids=tuple(data.get("recording_ids", ())),
        )
