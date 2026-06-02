"""``datasets.metadata`` — canonical metadata extraction.

Turns a decoded EDF reading + raw-file facts into the canonical
:class:`~datasets.schemas.metadata_record.MetadataRecord` plus the derived
:class:`~datasets.schemas.patient_record.PatientRecord` and
:class:`~datasets.schemas.recording_session.RecordingSession`. This is the single
place EDF header conventions (EDF+ patient/recording subfields, date encodings)
are interpreted, so the rest of the platform consumes one canonical shape.
"""

from __future__ import annotations

from datasets.metadata.extractor import (
    EXTRACTOR_VERSION,
    extract_metadata,
    extract_patient,
    extract_session,
)

__all__ = [
    "EXTRACTOR_VERSION",
    "extract_metadata",
    "extract_patient",
    "extract_session",
]
