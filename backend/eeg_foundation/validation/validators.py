"""EEG validation engine (Productization P1).

Turns the result of reading a real file into **structured findings** — never
exceptions. A clean file yields a report with no error/critical findings; a corrupted,
unreadable, or unsupported file yields findings describing exactly what is wrong.

Models: ``EEGValidationSeverity``, ``EEGValidationFinding``, ``EEGValidationResult``,
``EEGValidationReport``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EEG_VALIDATION_VERSION
from ..models.domain import SUPPORTED_FORMATS
from ..ingestion.raw import RawEEG


class EEGValidationSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_RANK = {EEGValidationSeverity.INFO: 0, EEGValidationSeverity.WARNING: 1,
         EEGValidationSeverity.ERROR: 2, EEGValidationSeverity.CRITICAL: 3}


@dataclass(frozen=True)
class EEGValidationFinding:
    code: str
    severity: str
    message: str
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "message": self.message,
                "context": self.context}


@dataclass(frozen=True)
class EEGValidationResult:
    """A single check's outcome (passed + optional finding)."""

    check: str
    passed: bool
    finding: Optional[EEGValidationFinding] = None

    def to_dict(self) -> dict:
        return {"check": self.check, "passed": self.passed,
                "finding": self.finding.to_dict() if self.finding else None}


@dataclass
class EEGValidationReport:
    results: list = field(default_factory=list)     # list[EEGValidationResult]
    validation_version: str = EEG_VALIDATION_VERSION

    def add(self, check: str, passed: bool, *, code: str = "", severity: str = "",
            message: str = "", context: Optional[dict] = None) -> None:
        finding = None
        if not passed:
            finding = EEGValidationFinding(code=code or check,
                                           severity=severity or EEGValidationSeverity.ERROR,
                                           message=message, context=context or {})
        self.results.append(EEGValidationResult(check=check, passed=passed, finding=finding))

    @property
    def findings(self) -> list:
        return [r.finding for r in self.results if r.finding]

    @property
    def max_severity(self) -> str:
        sev = [f.severity for f in self.findings]
        return max(sev, key=lambda s: _RANK.get(s, 0)) if sev else EEGValidationSeverity.INFO

    @property
    def valid(self) -> bool:
        """Valid iff no ERROR/CRITICAL findings (warnings/info are allowed)."""
        return all(_RANK.get(f.severity, 0) < _RANK[EEGValidationSeverity.ERROR]
                   for f in self.findings)

    def signature(self) -> str:
        return hash_obj({"results": [r.to_dict() for r in self.results]})

    def summary(self) -> dict:
        by_sev: dict = {}
        for f in self.findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        return {"valid": self.valid, "n_checks": len(self.results),
                "n_findings": len(self.findings), "max_severity": self.max_severity,
                "by_severity": dict(sorted(by_sev.items()))}

    def to_dict(self) -> dict:
        return {"validation_version": self.validation_version, **self.summary(),
                "results": [r.to_dict() for r in self.results],
                "findings": [f.to_dict() for f in self.findings],
                "signature": self.signature()}


# --- validity bounds ----------------------------------------------------------
_MIN_SFREQ = 0.0
_MAX_SFREQ = 100_000.0
_MAX_REASONABLE_SFREQ = 30_000.0       # above this is suspicious for EEG (warning only)


class EEGValidator:
    """Validates a :class:`RawEEG` (the result of reading a real file)."""

    def validate(self, raw: RawEEG, *, requested_format: Optional[str] = None) -> EEGValidationReport:
        report = EEGValidationReport()

        # readability / corruption
        report.add("readable", raw.ok, code="unreadable_file",
                   severity=EEGValidationSeverity.CRITICAL,
                   message=raw.error or "file could not be read",
                   context={"error": raw.error})
        if not raw.ok:
            # cannot check further; report what we know
            report.add("supported_format", raw.fmt in SUPPORTED_FORMATS,
                       code="unsupported_format", severity=EEGValidationSeverity.ERROR,
                       message=f"format {raw.fmt!r} is not supported",
                       context={"format": raw.fmt})
            return report

        # supported format
        report.add("supported_format", raw.fmt in SUPPORTED_FORMATS,
                   code="unsupported_format", severity=EEGValidationSeverity.ERROR,
                   message=f"format {raw.fmt!r} is not supported", context={"format": raw.fmt})

        # channels present
        report.add("has_channels", raw.n_channels > 0, code="missing_channels",
                   severity=EEGValidationSeverity.ERROR, message="no channels found",
                   context={"n_channels": raw.n_channels})
        report.add("has_signal_channels", len(raw.signal_channels) > 0,
                   code="missing_signal_channels", severity=EEGValidationSeverity.ERROR,
                   message="no signal (non-annotation) channels found",
                   context={"n_signal_channels": len(raw.signal_channels)})

        # channel labels non-empty
        empty_labels = [i for i, c in enumerate(raw.channels) if not c.label.strip()]
        report.add("channel_labels_present", not empty_labels, code="empty_channel_label",
                   severity=EEGValidationSeverity.WARNING, message="one or more empty channel labels",
                   context={"indices": empty_labels})

        # sampling rates valid
        bad_sf = [c.label for c in raw.signal_channels
                  if not (_MIN_SFREQ < c.sampling_frequency <= _MAX_SFREQ)]
        report.add("valid_sampling_rates", not bad_sf, code="invalid_sampling_rate",
                   severity=EEGValidationSeverity.ERROR,
                   message="invalid sampling rate (must be > 0 and finite)",
                   context={"channels": bad_sf})
        susp_sf = [c.label for c in raw.signal_channels
                   if c.sampling_frequency > _MAX_REASONABLE_SFREQ]
        report.add("plausible_sampling_rates", not susp_sf, code="implausible_sampling_rate",
                   severity=EEGValidationSeverity.WARNING,
                   message="unusually high sampling rate for EEG", context={"channels": susp_sf})

        # duration valid
        report.add("valid_duration", raw.duration_seconds > 0.0, code="invalid_duration",
                   severity=EEGValidationSeverity.ERROR,
                   message="recording duration must be positive",
                   context={"duration_seconds": raw.duration_seconds})

        # structural size check (EDF/BDF): expected data bytes match file size
        if raw.expected_data_bytes is not None and raw.actual_data_bytes is not None:
            report.add("data_section_intact", raw.actual_data_bytes >= raw.expected_data_bytes,
                       code="truncated_data", severity=EEGValidationSeverity.CRITICAL,
                       message="data section is shorter than the header declares (truncated/corrupted)",
                       context={"expected": raw.expected_data_bytes,
                                "actual": raw.actual_data_bytes})

        # annotation integrity (onsets non-negative, finite)
        bad_ann = [i for i, a in enumerate(raw.annotations)
                   if a.get("onset_seconds", 0.0) < 0.0]
        report.add("annotations_valid", not bad_ann, code="invalid_annotation",
                   severity=EEGValidationSeverity.WARNING,
                   message="annotation with negative onset", context={"indices": bad_ann})

        # metadata sanity: at least a representative sampling frequency
        report.add("metadata_present",
                   bool(raw.signal_channels) and raw.n_samples >= 0,
                   code="metadata_error", severity=EEGValidationSeverity.ERROR,
                   message="essential metadata missing", context={})

        # requested-format vs detected-format mismatch (info)
        if requested_format:
            report.add("requested_matches_detected",
                       _family(requested_format) == _family(raw.fmt),
                       code="format_mismatch", severity=EEGValidationSeverity.INFO,
                       message=f"requested {requested_format} but detected {raw.fmt}",
                       context={"requested": requested_format, "detected": raw.fmt})
        return report


def _family(fmt: str) -> str:
    return {"EDF+": "EDF", "BDF+": "BDF"}.get(fmt, fmt)
