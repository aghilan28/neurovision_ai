"""Validation, integrity, and quality report structures.

These are the *evidence* artifacts of the data lifecycle. They are deterministic
(given the same input the same report is produced) and serializable so they can
be persisted, hashed into lineage, and reproduced (AP-5/AP-6, NR-10/NR-11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datasets.schemas.enums import QualityState, ValidationSeverity, ValidationStatus


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single validation finding.

    ``code`` is a stable, machine-readable token (e.g. ``"HEADER_SIZE_MISMATCH"``)
    so issues can be filtered/asserted in tests without string matching on the
    human-readable ``message``. ``context`` carries structured detail and must be
    JSON-serializable.
    """

    code: str
    severity: ValidationSeverity
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationIssue:
        return cls(
            code=data["code"],
            severity=ValidationSeverity(data["severity"]),
            message=data["message"],
            context=dict(data.get("context", {})),
        )


@dataclass(frozen=True, slots=True)
class IntegrityResult:
    """Outcome of binary integrity verification of an EDF file."""

    ok: bool
    expected_size_bytes: int
    actual_size_bytes: int
    declared_data_records: int
    computed_data_records: int
    record_size_bytes: int
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "expected_size_bytes": self.expected_size_bytes,
            "actual_size_bytes": self.actual_size_bytes,
            "declared_data_records": self.declared_data_records,
            "computed_data_records": self.computed_data_records,
            "record_size_bytes": self.record_size_bytes,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrityResult:
        return cls(
            ok=bool(data["ok"]),
            expected_size_bytes=int(data["expected_size_bytes"]),
            actual_size_bytes=int(data["actual_size_bytes"]),
            declared_data_records=int(data["declared_data_records"]),
            computed_data_records=int(data["computed_data_records"]),
            record_size_bytes=int(data["record_size_bytes"]),
            notes=tuple(data.get("notes", ())),
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Aggregate report from a validation run over one record.

    ``status`` is derived from the issues: any ``ERROR`` -> ``FAILED``; otherwise
    any ``WARNING`` -> ``PASSED_WITH_WARNINGS``; otherwise ``PASSED``.
    """

    file_id: str
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...] = ()
    checks_run: tuple[str, ...] = ()
    validator_version: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity is ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity is ValidationSeverity.WARNING)

    @staticmethod
    def status_for(issues: tuple[ValidationIssue, ...]) -> ValidationStatus:
        if any(i.severity is ValidationSeverity.ERROR for i in issues):
            return ValidationStatus.FAILED
        if any(i.severity is ValidationSeverity.WARNING for i in issues):
            return ValidationStatus.PASSED_WITH_WARNINGS
        return ValidationStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "status": self.status.value,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "checks_run": list(self.checks_run),
            "validator_version": self.validator_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationReport:
        return cls(
            file_id=data["file_id"],
            status=ValidationStatus(data["status"]),
            issues=tuple(ValidationIssue.from_dict(i) for i in data.get("issues", [])),
            checks_run=tuple(data.get("checks_run", ())),
            validator_version=data.get("validator_version", ""),
        )


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Quality posture of a record at the data layer.

    The data foundation **reports** quality; it never removes data. The richer
    *signal* quality assessment is owned by ``preprocessing/quality``; this report
    captures coarse, file-level quality observations (e.g. zero-duration,
    no data channels).
    """

    file_id: str
    state: QualityState
    issues: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "state": self.state.value,
            "issues": [i.to_dict() for i in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityReport:
        return cls(
            file_id=data["file_id"],
            state=QualityState(data["state"]),
            issues=tuple(ValidationIssue.from_dict(i) for i in data.get("issues", [])),
        )
