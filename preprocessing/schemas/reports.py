"""Report / evidence structures for preprocessing.

These deterministic, serializable structures capture *what happened* at each stage
(``StageResult``), the *specification* of each filter applied (``FilterSpec``), the
*verification* of a filter's frequency response (``FrequencyResponseCheck``), the
*montage* outcome (``MontageResult``), and the *quality* and *validation* verdicts.
Quality findings are **report-only**: the pipeline never removes data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from preprocessing.schemas.enums import QualitySeverity, StageName, StageStatus


@dataclass(frozen=True, slots=True)
class StageResult:
    """The outcome of running one pipeline stage."""

    stage: StageName
    status: StageStatus
    operation_version: str
    params_fingerprint: str | None = None
    input_fingerprint: str | None = None
    output_fingerprint: str | None = None
    messages: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "operation_version": self.operation_version,
            "params_fingerprint": self.params_fingerprint,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "messages": list(self.messages),
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageResult:
        return cls(
            stage=StageName(data["stage"]),
            status=StageStatus(data["status"]),
            operation_version=data["operation_version"],
            params_fingerprint=data.get("params_fingerprint"),
            input_fingerprint=data.get("input_fingerprint"),
            output_fingerprint=data.get("output_fingerprint"),
            messages=tuple(data.get("messages", ())),
            details=dict(data.get("details", {})),
        )


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """The specification of a single filter that was (or would be) applied."""

    kind: str  # "bandpass" | "notch" | "detrend"
    description: str
    parameters: dict[str, Any]
    sampling_rate_hz: float
    zero_phase: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "parameters": self.parameters,
            "sampling_rate_hz": self.sampling_rate_hz,
            "zero_phase": self.zero_phase,
        }


@dataclass(frozen=True, slots=True)
class FrequencyResponseCheck:
    """Verification that a designed filter's response meets its specification.

    ``measured_db`` maps a probe frequency (Hz, as a string key for JSON) to the
    filter's magnitude response in dB. ``passed`` is the conjunction of all
    passband/stopband assertions.
    """

    kind: str
    passed: bool
    measured_db: dict[str, float]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "passed": self.passed,
            "measured_db": self.measured_db,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class MontageResult:
    """Outcome of applying a montage."""

    montage_type: str
    montage_name: str
    output_channels: tuple[str, ...]
    missing_channels: tuple[str, ...] = ()
    skipped_derivations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "montage_type": self.montage_type,
            "montage_name": self.montage_name,
            "output_channels": list(self.output_channels),
            "missing_channels": list(self.missing_channels),
            "skipped_derivations": list(self.skipped_derivations),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class QualityIssue:
    """A single signal-quality finding (report-only)."""

    code: str
    severity: QualitySeverity
    message: str
    channel: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "channel": self.channel,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityIssue:
        return cls(
            code=data["code"],
            severity=QualitySeverity(data["severity"]),
            message=data["message"],
            channel=data.get("channel"),
            context=dict(data.get("context", {})),
        )


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Aggregated signal-quality findings for a recording (never mutates data)."""

    issues: tuple[QualityIssue, ...] = ()
    checks_run: tuple[str, ...] = ()
    quality_version: str = ""

    @property
    def has_critical(self) -> bool:
        return any(i.severity is QualitySeverity.CRITICAL for i in self.issues)

    @property
    def flagged_channels(self) -> tuple[str, ...]:
        return tuple(sorted({i.channel for i in self.issues if i.channel}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "checks_run": list(self.checks_run),
            "quality_version": self.quality_version,
            "has_critical": self.has_critical,
            "flagged_channels": list(self.flagged_channels),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityReport:
        return cls(
            issues=tuple(QualityIssue.from_dict(i) for i in data.get("issues", [])),
            checks_run=tuple(data.get("checks_run", ())),
            quality_version=data.get("quality_version", ""),
        )


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single input/output validation finding."""

    code: str
    severity: str  # "error" | "warning" | "info"
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationIssue:
        return cls(
            code=data["code"],
            severity=data["severity"],
            message=data["message"],
            context=dict(data.get("context", {})),
        )


@dataclass(frozen=True, slots=True)
class PreprocessingValidationReport:
    """Input/output validation verdict for a pipeline stage boundary."""

    scope: str  # "input" | "output" | "channel"
    ok: bool
    issues: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PreprocessingValidationReport:
        return cls(
            scope=data["scope"],
            ok=bool(data["ok"]),
            issues=tuple(ValidationIssue.from_dict(i) for i in data.get("issues", [])),
        )
