"""Input / channel / output validators for the preprocessing pipeline."""

from __future__ import annotations

import numpy as np

from preprocessing.montages.definitions import MontageDefinition
from preprocessing.montages.mapping import build_channel_index
from preprocessing.schemas.reports import PreprocessingValidationReport, ValidationIssue
from preprocessing.schemas.signal import RawRecording
from preprocessing.schemas.windows import WindowSet

#: Version of the validation operation (recorded on lineage).
VALIDATION_OP_VERSION = "1.0.0"

_ERROR = "error"
_WARNING = "warning"


def _report(scope: str, issues: list[ValidationIssue]) -> PreprocessingValidationReport:
    ok = not any(i.severity == _ERROR for i in issues)
    return PreprocessingValidationReport(scope=scope, ok=ok, issues=tuple(issues))


def validate_input(recording: RawRecording) -> PreprocessingValidationReport:
    """Validate the incoming recording's structural well-formedness."""
    issues: list[ValidationIssue] = []
    arr = recording.signals

    if arr.ndim != 2:
        issues.append(
            ValidationIssue("BAD_SHAPE", _ERROR, "signals must be 2-D (channels, samples)",
                            {"ndim": int(arr.ndim)})
        )
        return _report("input", issues)

    if arr.shape[0] == 0:
        issues.append(ValidationIssue("NO_CHANNELS", _ERROR, "recording has no channels"))
    if arr.shape[1] == 0:
        issues.append(ValidationIssue("NO_SAMPLES", _ERROR, "recording has no samples"))
    if arr.shape[0] != len(recording.channel_names):
        issues.append(
            ValidationIssue(
                "CHANNEL_COUNT_MISMATCH",
                _ERROR,
                "signal rows do not match channel-name count",
                {"rows": int(arr.shape[0]), "names": len(recording.channel_names)},
            )
        )
    if recording.sampling_rate_hz <= 0:
        issues.append(
            ValidationIssue("INVALID_SAMPLING_RATE", _ERROR, "sampling rate must be positive",
                            {"sampling_rate_hz": recording.sampling_rate_hz})
        )
    if arr.size and not np.all(np.isfinite(arr)):
        issues.append(
            ValidationIssue(
                "NONFINITE_INPUT",
                _WARNING,
                "input contains non-finite samples (see quality report for detail)",
                {"nonfinite": int(np.count_nonzero(~np.isfinite(arr)))},
            )
        )
    return _report("input", issues)


def validate_channels(
    recording: RawRecording, definition: MontageDefinition
) -> PreprocessingValidationReport:
    """Validate that the montage's required channels are present."""
    issues: list[ValidationIssue] = []
    required = definition.required_channels
    if required:
        index = build_channel_index(recording.channel_names)
        missing = [ch for ch in required if ch not in index]
        if missing:
            issues.append(
                ValidationIssue(
                    "MISSING_REQUIRED_CHANNELS",
                    _ERROR,
                    "montage requires channels that are absent",
                    {"montage": definition.name, "missing": missing},
                )
            )
    return _report("channel", issues)


def validate_output_signal(signals: np.ndarray, n_channels: int) -> PreprocessingValidationReport:
    """Validate an intermediate processed signal (finite, expected channel count)."""
    issues: list[ValidationIssue] = []
    if signals.ndim != 2:
        issues.append(ValidationIssue("BAD_SHAPE", _ERROR, "processed signal must be 2-D"))
        return _report("output", issues)
    if signals.shape[0] != n_channels:
        issues.append(
            ValidationIssue("CHANNEL_COUNT_CHANGED_UNEXPECTEDLY", _WARNING,
                            "channel count differs from expected",
                            {"got": int(signals.shape[0]), "expected": n_channels})
        )
    if signals.size and not np.all(np.isfinite(signals)):
        issues.append(
            ValidationIssue("NONFINITE_OUTPUT", _ERROR,
                            "processing introduced non-finite samples",
                            {"nonfinite": int(np.count_nonzero(~np.isfinite(signals)))})
        )
    return _report("output", issues)


def validate_output_windows(window_set: WindowSet) -> PreprocessingValidationReport:
    """Validate the final window set (3-D, consistent shapes, finite)."""
    issues: list[ValidationIssue] = []
    data = window_set.data
    if data.ndim != 3:
        issues.append(ValidationIssue("BAD_SHAPE", _ERROR, "window data must be 3-D"))
        return _report("output", issues)
    if data.shape[1] != len(window_set.channel_names):
        issues.append(
            ValidationIssue("CHANNEL_COUNT_MISMATCH", _ERROR,
                            "window channel axis does not match channel names",
                            {"axis": int(data.shape[1]), "names": len(window_set.channel_names)})
        )
    if data.shape[0] != len(window_set.windows):
        issues.append(
            ValidationIssue("WINDOW_METADATA_MISMATCH", _ERROR,
                            "window count does not match metadata count",
                            {"windows": int(data.shape[0]), "metadata": len(window_set.windows)})
        )
    if data.size and not np.all(np.isfinite(data)):
        issues.append(
            ValidationIssue("NONFINITE_OUTPUT", _ERROR,
                            "windowed output contains non-finite samples")
        )
    return _report("output", issues)
