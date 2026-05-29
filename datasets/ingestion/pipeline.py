"""The deterministic EDF ingestion pipeline.

``ingest_edf_file`` is the single entry point that takes a file path and produces a
fully-populated :class:`~datasets.schemas.validated_record.ValidatedEegRecord` with
optional lineage. The pipeline is deterministic: for a given file (and a given
optional context) it always produces the same record and the same reports.

Lifecycle (Project directive):
    detect format -> hash -> read -> extract metadata -> verify integrity ->
    validate -> derive patient/session -> (optional) record lineage.

Outcomes
--------
* **Readable EDF/EDF+ that passes validation** -> status ``VALIDATED``.
* **Readable but validation ERROR** (e.g. corruption, invalid metadata) ->
  status ``QUARANTINED`` (the record exists and is fully traceable, but is not
  fit to enter a dataset).
* **Unsupported format / unreadable bytes** -> :class:`IngestionError`, which
  carries the :class:`ValidationReport` so the failure is still structured
  evidence, not an opaque crash.
"""

from __future__ import annotations

import os

from datasets._canonical import sha256_file
from datasets.ingestion.edf_reader import EdfReadError, read_edf
from datasets.ingestion.integrity import verify_integrity
from datasets.ingestion.signature import detect_format
from datasets.lineage.tracker import LineageTracker, build_ingestion_lineage
from datasets.metadata.extractor import extract_metadata, extract_patient, extract_session
from datasets.schemas.enums import FileFormat, QualityState, RecordStatus, ValidationSeverity
from datasets.schemas.raw_eeg_file import RawEegFile
from datasets.schemas.reports import QualityReport, ValidationIssue, ValidationReport
from datasets.schemas.validated_record import ValidatedEegRecord
from datasets.validation.report import build_report
from datasets.validation.validators import ValidationContext, run_all_checks


class IngestionError(RuntimeError):
    """Raised when a file cannot be ingested as EDF/EDF+.

    Attributes
    ----------
    report:
        A :class:`ValidationReport` describing *why* ingestion failed.
    raw_file:
        The :class:`RawEegFile` (identity/format) when it could be determined.
    """

    def __init__(self, message: str, report: ValidationReport, raw_file: RawEegFile | None) -> None:
        super().__init__(message)
        self.report = report
        self.raw_file = raw_file


def _file_id_for(content_sha256: str) -> str:
    return f"edf-{content_sha256[:16]}"


def _quality_for(record_issues: ValidationReport) -> QualityState:
    return QualityState.FLAGGED if record_issues.warning_count or record_issues.error_count else QualityState.OK


def ingest_edf_file(
    path: str,
    *,
    content_sha256: str | None = None,
    context: ValidationContext | None = None,
    tracker: LineageTracker | None = None,
    recorded_at: str | None = None,
) -> ValidatedEegRecord:
    """Ingest one EDF/EDF+ file deterministically.

    Parameters
    ----------
    path:
        Path to the EDF/EDF+ file.
    content_sha256:
        Precomputed content hash (optional; computed if omitted). Supplying it lets
        callers avoid re-hashing a file they already hashed.
    context:
        Optional :class:`ValidationContext` (expected channels, known hashes for
        duplicate detection).
    tracker:
        Optional :class:`LineageTracker`; when provided, the ingestion provenance
        chain is recorded and the record's ``lineage_id`` is populated.
    recorded_at:
        Optional caller-supplied timestamp for provenance (never read from the
        wall clock here, to keep ingestion reproducible).
    """
    if not os.path.isfile(path):
        report = build_report(
            file_id="unknown",
            issues=[
                ValidationIssue(
                    code="FILE_NOT_FOUND",
                    severity=ValidationSeverity.ERROR,
                    message=f"no readable file at {path!r}",
                )
            ],
            checks_run=("readability",),
        )
        raise IngestionError(f"file not found: {path!r}", report, None)

    sha = content_sha256 or sha256_file(path)
    file_id = _file_id_for(sha)
    file_size = os.path.getsize(path)
    file_format = detect_format(path)
    raw_file = RawEegFile(
        file_id=file_id,
        content_sha256=sha,
        file_name=os.path.basename(path),
        file_size_bytes=file_size,
        detected_format=file_format,
        source_path=path,
    )

    # Unsupported / unknown formats: report and stop (cannot build metadata).
    if not file_format.is_supported:
        issues = [
            ValidationIssue(
                code="UNSUPPORTED_FORMAT" if file_format is FileFormat.UNSUPPORTED else "UNKNOWN_FORMAT",
                severity=ValidationSeverity.ERROR,
                message="V1 supports EDF/EDF+ only; this file is not a supported EDF container",
                context={"detected_format": file_format.value},
            )
        ]
        report = build_report(file_id, issues, ("readability", "format"))
        raise IngestionError(f"unsupported format for {path!r}", report, raw_file)

    # Parse: header + annotations (no float materialization needed for ingestion).
    try:
        reading = read_edf(path, load_signals=True, materialize_signals=False)
    except EdfReadError as exc:
        issues = [
            ValidationIssue(
                code="EDF_PARSE_ERROR",
                severity=ValidationSeverity.ERROR,
                message=f"could not parse EDF/EDF+ structure: {exc.message}",
                context={"reader_code": exc.code},
            )
        ]
        report = build_report(file_id, issues, ("readability", "format", "parse"))
        raise IngestionError(f"unreadable EDF for {path!r}", report, raw_file) from exc

    # Canonical metadata + integrity.
    metadata = extract_metadata(reading, content_sha256=sha, file_format=file_format)
    integrity = verify_integrity(path, reading.header)

    # Validation (all checks).
    issues, checks_run = run_all_checks(
        metadata=metadata,
        integrity=integrity,
        file_format=file_format,
        content_sha256=sha,
        context=context,
    )
    validation = build_report(file_id, issues, checks_run)

    # Derived patient/session.
    patient = extract_patient(metadata, content_sha256=sha)
    session = extract_session(metadata)

    quality = QualityReport(
        file_id=file_id,
        state=_quality_for(validation),
        issues=tuple(i for i in validation.issues if i.severity is not ValidationSeverity.INFO),
    )

    status = RecordStatus.VALIDATED if validation.status.is_acceptable else RecordStatus.QUARANTINED

    lineage_id: str | None = None
    if tracker is not None:
        lineage_id = build_ingestion_lineage(
            tracker, raw_file, validation, metadata, recorded_at=recorded_at
        )

    return ValidatedEegRecord(
        raw_file=raw_file,
        metadata=metadata,
        patient=patient,
        session=session,
        validation=validation,
        quality=quality,
        status=status,
        lineage_id=lineage_id,
    )
