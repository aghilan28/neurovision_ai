"""Individual, composable EDF validation checks.

Each ``validate_*`` function takes already-extracted, structured inputs and
returns a list of :class:`~datasets.schemas.reports.ValidationIssue`. Functions are
pure and deterministic: the same inputs always yield the same issues in the same
order. Severity convention:

* ``ERROR``   — the record must not proceed (it is quarantined).
* ``WARNING`` — the record may proceed but a human should be aware.
* ``INFO``    — neutral, recorded for traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datasets.schemas.enums import FileFormat, ValidationSeverity
from datasets.schemas.metadata_record import MetadataRecord
from datasets.schemas.reports import IntegrityResult, ValidationIssue


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Optional context that parameterizes some checks.

    ``expected_channels`` enables missing-channel detection (compared
    case-insensitively against canonical labels). ``known_sha256`` enables
    duplicate detection against records already known to the system.
    """

    expected_channels: tuple[str, ...] = ()
    known_sha256: frozenset[str] = field(default_factory=frozenset)


def _issue(code: str, severity: ValidationSeverity, message: str, **context: object) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, message=message, context=dict(context))


def validate_format(file_format: FileFormat) -> list[ValidationIssue]:
    """Reject formats outside the V1-supported set (EDF / EDF+)."""
    if file_format.is_supported:
        return []
    if file_format is FileFormat.UNSUPPORTED:
        return [
            _issue(
                "UNSUPPORTED_FORMAT",
                ValidationSeverity.ERROR,
                "file is a recognized but unsupported format (V1 supports EDF/EDF+ only)",
            )
        ]
    return [
        _issue(
            "UNKNOWN_FORMAT",
            ValidationSeverity.ERROR,
            "file is not a recognizable EDF/EDF+ container",
        )
    ]


def validate_integrity(integrity: IntegrityResult) -> list[ValidationIssue]:
    """Flag binary corruption / truncation from an integrity result."""
    issues: list[ValidationIssue] = []
    if not integrity.ok:
        issues.append(
            _issue(
                "FILE_INTEGRITY_MISMATCH",
                ValidationSeverity.ERROR,
                "file size does not match the header-declared record layout (possible corruption)",
                expected_size_bytes=integrity.expected_size_bytes,
                actual_size_bytes=integrity.actual_size_bytes,
                declared_data_records=integrity.declared_data_records,
                computed_data_records=integrity.computed_data_records,
            )
        )
    for note in integrity.notes:
        issues.append(
            _issue("INTEGRITY_NOTE", ValidationSeverity.INFO, note)
        )
    return issues


def validate_channels(metadata: MetadataRecord) -> list[ValidationIssue]:
    """Check channel-set consistency (presence, duplicates, data channels)."""
    issues: list[ValidationIssue] = []
    if metadata.channel_count == 0:
        issues.append(
            _issue("NO_CHANNELS", ValidationSeverity.ERROR, "file declares zero signals")
        )
        return issues

    if metadata.data_channel_count == 0:
        issues.append(
            _issue(
                "NO_DATA_CHANNELS",
                ValidationSeverity.ERROR,
                "file has no data channels (only annotation/non-signal channels)",
            )
        )

    labels = [c.label for c in metadata.data_channels]
    seen: dict[str, int] = {}
    for label in labels:
        seen[label] = seen.get(label, 0) + 1
    duplicates = sorted(label for label, count in seen.items() if count > 1)
    if duplicates:
        issues.append(
            _issue(
                "DUPLICATE_CHANNEL_LABELS",
                ValidationSeverity.WARNING,
                "duplicate data-channel labels detected",
                labels=duplicates,
            )
        )
    return issues


def validate_sampling(metadata: MetadataRecord) -> list[ValidationIssue]:
    """Check sampling-rate validity and consistency across data channels."""
    issues: list[ValidationIssue] = []
    rates = metadata.sampling_frequencies_hz
    if not rates:
        return issues

    if any(r <= 0 for r in rates):
        issues.append(
            _issue(
                "INVALID_SAMPLING_RATE",
                ValidationSeverity.ERROR,
                "one or more data channels have a non-positive sampling rate",
                rates=list(rates),
            )
        )

    distinct = sorted(set(rates))
    if len(distinct) > 1:
        issues.append(
            _issue(
                "NON_UNIFORM_SAMPLING",
                ValidationSeverity.WARNING,
                "data channels do not share a single sampling rate",
                distinct_rates=distinct,
            )
        )
    return issues


def validate_metadata(metadata: MetadataRecord) -> list[ValidationIssue]:
    """Check header-derived metadata for invalid / suspicious values."""
    issues: list[ValidationIssue] = []
    tech = metadata.technical

    if tech.record_duration_seconds <= 0:
        issues.append(
            _issue(
                "INVALID_RECORD_DURATION",
                ValidationSeverity.ERROR,
                "data-record duration must be positive",
                record_duration_seconds=tech.record_duration_seconds,
            )
        )

    if metadata.duration_seconds <= 0:
        issues.append(
            _issue(
                "ZERO_DURATION",
                ValidationSeverity.WARNING,
                "recording has zero total duration",
            )
        )

    for c in metadata.data_channels:
        if c.digital_max <= c.digital_min:
            issues.append(
                _issue(
                    "DEGENERATE_DIGITAL_RANGE",
                    ValidationSeverity.WARNING,
                    "channel has a non-increasing digital range (calibration is undefined)",
                    channel=c.label,
                    digital_min=c.digital_min,
                    digital_max=c.digital_max,
                )
            )
        if c.physical_max == c.physical_min:
            issues.append(
                _issue(
                    "DEGENERATE_PHYSICAL_RANGE",
                    ValidationSeverity.WARNING,
                    "channel has a zero physical range",
                    channel=c.label,
                )
            )

    if not metadata.extra.get("patient_identity_present", False):
        issues.append(
            _issue(
                "MISSING_PATIENT_IDENTITY",
                ValidationSeverity.WARNING,
                "no patient identity in header; treated as a distinct patient "
                "(conservative for patient-disjoint validation, NR-3)",
            )
        )
    return issues


def validate_missing_channels(
    metadata: MetadataRecord, expected_channels: tuple[str, ...]
) -> list[ValidationIssue]:
    """Detect required channels that are absent (case-insensitive on labels)."""
    if not expected_channels:
        return []
    present = {c.label.upper() for c in metadata.data_channels}
    missing = sorted(ch for ch in expected_channels if ch.upper() not in present)
    if missing:
        return [
            _issue(
                "MISSING_EXPECTED_CHANNELS",
                ValidationSeverity.ERROR,
                "one or more expected channels are missing",
                missing=missing,
            )
        ]
    return []


def validate_duplicate(
    content_sha256: str, known_sha256: frozenset[str]
) -> list[ValidationIssue]:
    """Detect that this exact file content was already ingested."""
    if content_sha256 in known_sha256:
        return [
            _issue(
                "DUPLICATE_RECORD",
                ValidationSeverity.WARNING,
                "an identical file (by content hash) is already known to the system",
                content_sha256=content_sha256,
            )
        ]
    return []


def run_all_checks(
    metadata: MetadataRecord,
    integrity: IntegrityResult,
    file_format: FileFormat,
    content_sha256: str,
    context: ValidationContext | None = None,
) -> tuple[list[ValidationIssue], tuple[str, ...]]:
    """Run every applicable check and return ``(issues, checks_run)``.

    The set of checks run is recorded so a report transparently states what was
    evaluated (auditability, AP-8).
    """
    ctx = context or ValidationContext()
    issues: list[ValidationIssue] = []
    checks: list[str] = []

    issues += validate_format(file_format)
    checks.append("format")
    issues += validate_integrity(integrity)
    checks.append("integrity")
    issues += validate_channels(metadata)
    checks.append("channels")
    issues += validate_sampling(metadata)
    checks.append("sampling")
    issues += validate_metadata(metadata)
    checks.append("metadata")
    issues += validate_missing_channels(metadata, ctx.expected_channels)
    checks.append("missing_channels")
    issues += validate_duplicate(content_sha256, ctx.known_sha256)
    checks.append("duplicate")

    return issues, tuple(checks)
