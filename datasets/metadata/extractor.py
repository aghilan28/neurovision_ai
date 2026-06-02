"""Canonical metadata extraction from a decoded EDF reading.

Interprets EDF / EDF+ header conventions deterministically:

* **Patient identity** is derived from the EDF+ patient code subfield when present;
  otherwise it falls back to the raw patient field, and finally to the file's
  content hash. Unknown identities are therefore treated as *distinct* patients —
  the conservative choice that can never create cross-patient leakage (AP-2/NR-3).
  When identity is absent, a structured signal is left in ``extra`` for the
  validator to surface.
* **Dates** use the EDF 2-digit-year clipping rule (1985–2084); EDF+ ``Startdate``
  in the recording field is preferred when available.

No wall-clock is read here: any "now" timestamps are caller-supplied, keeping
extraction a pure function of the input (reproducibility, AP-6/NR-10).
"""

from __future__ import annotations

from datasets._canonical import mint_id
from datasets.ingestion.discovery import (
    discover_channels,
    discover_duration_seconds,
    discover_reference,
)
from datasets.ingestion.edf_reader import EdfReading
from datasets.schemas.enums import FileFormat
from datasets.schemas.metadata_record import (
    Annotation,
    MetadataRecord,
    TechnicalMetadata,
)
from datasets.schemas.patient_record import PatientRecord
from datasets.schemas.recording_session import RecordingSession

#: Metadata-extractor version (recorded on every MetadataRecord for traceability).
EXTRACTOR_VERSION = "1.0.0"

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _file_id_for(content_sha256: str) -> str:
    return f"edf-{content_sha256[:16]}"


def _recording_id_for(content_sha256: str) -> str:
    return f"rec-{content_sha256[:16]}"


def _parse_edf_short_date(start_date: str) -> str | None:
    """Parse EDF ``dd.mm.yy`` into ISO ``YYYY-MM-DD`` using the 1985–2084 rule."""
    parts = start_date.split(".")
    if len(parts) != 3:
        return None
    try:
        day, month, yy = (int(p) for p in parts)
    except ValueError:
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    year = 1900 + yy if yy >= 85 else 2000 + yy
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_edfplus_startdate(recording_field: str) -> str | None:
    """Parse EDF+ recording field ``Startdate dd-MMM-yyyy ...`` into ISO date."""
    tokens = recording_field.split()
    if len(tokens) < 2 or tokens[0].lower() != "startdate":
        return None
    date_token = tokens[1]
    bits = date_token.split("-")
    if len(bits) != 3:
        return None
    try:
        day = int(bits[0])
        month = _MONTHS.get(bits[1].upper())
        year = int(bits[2])
    except ValueError:
        return None
    if month is None or not (1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _normalize_time(start_time: str) -> str | None:
    """Normalize EDF ``hh.mm.ss`` to ``HH:MM:SS`` (or ``None`` if malformed)."""
    parts = start_time.split(".")
    if len(parts) != 3:
        return None
    try:
        h, m, s = (int(p) for p in parts)
    except ValueError:
        return None
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
        return None
    return f"{h:02d}:{m:02d}:{s:02d}"


def _patient_subfields(patient_field: str) -> list[str]:
    return patient_field.split()


def _derive_patient_identity(
    patient_field: str,
    file_format: FileFormat,
    content_sha256: str,
) -> tuple[str, str | None, str | None, bool]:
    """Return ``(patient_id, sex, birthdate_iso, identity_present)``."""
    sex: str | None = None
    birthdate_iso: str | None = None
    identity_source: str | None = None
    identity_present = False

    is_edf_plus = file_format in (FileFormat.EDF_PLUS_C, FileFormat.EDF_PLUS_D)
    fields = _patient_subfields(patient_field)

    if is_edf_plus and fields:
        code = fields[0]
        if code and code != "X":
            identity_source = code
            identity_present = True
        if len(fields) >= 2 and fields[1] in {"M", "F", "X"}:
            sex = None if fields[1] == "X" else fields[1]
        if len(fields) >= 3 and fields[2] != "X":
            bits = fields[2].split("-")
            if len(bits) == 3:
                try:
                    bday = int(bits[0])
                    bmonth = _MONTHS.get(bits[1].upper())
                    byear = int(bits[2])
                    if bmonth is not None and 1 <= bday <= 31:
                        birthdate_iso = f"{byear:04d}-{bmonth:02d}-{bday:02d}"
                except ValueError:
                    birthdate_iso = None
    elif patient_field and patient_field != "X":
        identity_source = patient_field
        identity_present = True

    if identity_source is None:
        # Conservative fallback: each unidentified file is its own patient.
        identity_source = f"anonymous:{content_sha256}"

    patient_id = mint_id("patient", identity_source)
    return patient_id, sex, birthdate_iso, identity_present


def _recording_admin(recording_field: str) -> tuple[str | None, str | None]:
    """Extract ``(admin_code, equipment)`` from an EDF+ recording field if present."""
    tokens = recording_field.split()
    if len(tokens) >= 1 and tokens[0].lower() == "startdate":
        admin_code = tokens[3] if len(tokens) >= 4 and tokens[3] != "X" else None
        equipment = tokens[5] if len(tokens) >= 6 and tokens[5] != "X" else None
        return admin_code, equipment
    return None, None


def extract_metadata(
    reading: EdfReading,
    *,
    content_sha256: str,
    file_format: FileFormat,
) -> MetadataRecord:
    """Build the canonical :class:`MetadataRecord` from a decoded reading."""
    header = reading.header
    file_id = _file_id_for(content_sha256)
    recording_id = _recording_id_for(content_sha256)

    patient_id, _sex, _bday, identity_present = _derive_patient_identity(
        header.patient_field, file_format, content_sha256
    )

    recording_date_iso = _parse_edfplus_startdate(header.recording_field) or _parse_edf_short_date(
        header.start_date
    )

    channels = discover_channels(header)
    reference = discover_reference(header)
    duration = discover_duration_seconds(header)

    annotations = tuple(
        Annotation(onset_seconds=onset, duration_seconds=duration_s, text=text)
        for (onset, duration_s, text) in reading.annotations
    )

    technical = TechnicalMetadata(
        edf_version_field=header.version_field,
        reserved_field=header.reserved,
        header_bytes=header.header_bytes,
        num_data_records=header.num_data_records,
        record_duration_seconds=header.record_duration_seconds,
        num_signals=header.num_signals,
        raw_patient_field=header.patient_field,
        raw_recording_field=header.recording_field,
    )

    return MetadataRecord(
        file_id=file_id,
        patient_id=patient_id,
        recording_id=recording_id,
        dataset_id=None,
        file_format=file_format,
        start_date=header.start_date,
        start_time=header.start_time,
        recording_date_iso=recording_date_iso,
        duration_seconds=duration,
        channels=channels,
        reference=reference,
        technical=technical,
        annotations=annotations,
        extractor_version=EXTRACTOR_VERSION,
        extra={"patient_identity_present": identity_present},
    )


def extract_patient(
    metadata: MetadataRecord,
    *,
    content_sha256: str,
) -> PatientRecord:
    """Derive the :class:`PatientRecord` for a metadata record."""
    _pid, sex, birthdate_iso, _present = _derive_patient_identity(
        metadata.technical.raw_patient_field,
        metadata.file_format,
        content_sha256,
    )
    return PatientRecord(
        patient_id=metadata.patient_id,
        raw_patient_field=metadata.technical.raw_patient_field,
        sex=sex,
        birthdate_iso=birthdate_iso,
        recording_ids=(metadata.recording_id,),
    )


def extract_session(metadata: MetadataRecord) -> RecordingSession:
    """Derive the :class:`RecordingSession` for a metadata record."""
    time_iso = _normalize_time(metadata.start_time)
    start_dt_iso: str | None = None
    if metadata.recording_date_iso and time_iso:
        start_dt_iso = f"{metadata.recording_date_iso}T{time_iso}"

    admin_code, equipment = _recording_admin(metadata.technical.raw_recording_field)

    return RecordingSession(
        recording_id=metadata.recording_id,
        patient_id=metadata.patient_id,
        file_id=metadata.file_id,
        start_date=metadata.start_date,
        start_time=metadata.start_time,
        duration_seconds=metadata.duration_seconds,
        start_datetime_iso=start_dt_iso,
        equipment=equipment,
        admin_code=admin_code,
    )
