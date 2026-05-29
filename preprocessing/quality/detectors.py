"""Signal-quality detectors (pure, deterministic, report-only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from preprocessing.schemas.enums import QualitySeverity
from preprocessing.schemas.reports import QualityIssue

#: Version of the quality operation (recorded on lineage).
QUALITY_OP_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class QualityThresholds:
    """Tunable thresholds for the quality detectors (all explicit, no magic)."""

    flat_std: float = 1e-6  # below this per-channel std ⇒ "flat"
    amplitude_uv: float = 500.0  # |x| above this ⇒ amplitude/saturation concern
    mains_hz: float = 60.0  # power-line frequency to probe
    mains_ratio: float = 0.5  # mains-band / total power above this ⇒ line noise
    clipping_run: int = 50  # consecutive identical extreme samples ⇒ clipping


def detect_missing_channels(
    channel_names: tuple[str, ...], expected_channels: tuple[str, ...]
) -> list[QualityIssue]:
    """Report expected channels that are absent (case-insensitive)."""
    if not expected_channels:
        return []
    present = {c.upper() for c in channel_names}
    issues: list[QualityIssue] = []
    for ch in expected_channels:
        if ch.upper() not in present:
            issues.append(
                QualityIssue(
                    code="MISSING_CHANNEL",
                    severity=QualitySeverity.WARNING,
                    message="expected channel is absent",
                    channel=ch,
                )
            )
    return issues


def detect_invalid_channels(
    signals: np.ndarray, channel_names: tuple[str, ...]
) -> list[QualityIssue]:
    """Report channels that are entirely non-finite (NaN/Inf)."""
    issues: list[QualityIssue] = []
    for i, name in enumerate(channel_names):
        row = signals[i]
        if row.size and not np.any(np.isfinite(row)):
            issues.append(
                QualityIssue(
                    code="INVALID_CHANNEL",
                    severity=QualitySeverity.CRITICAL,
                    message="channel contains no finite samples",
                    channel=name,
                )
            )
    return issues


def detect_sampling_issues(
    sampling_rate_hz: float, min_required_hz: float = 0.0
) -> list[QualityIssue]:
    """Report a non-positive or insufficient sampling rate."""
    issues: list[QualityIssue] = []
    if sampling_rate_hz <= 0:
        issues.append(
            QualityIssue(
                code="INVALID_SAMPLING_RATE",
                severity=QualitySeverity.CRITICAL,
                message="sampling rate is non-positive",
                context={"sampling_rate_hz": sampling_rate_hz},
            )
        )
    elif min_required_hz > 0 and sampling_rate_hz < min_required_hz:
        issues.append(
            QualityIssue(
                code="LOW_SAMPLING_RATE",
                severity=QualitySeverity.WARNING,
                message="sampling rate below the required minimum",
                context={"sampling_rate_hz": sampling_rate_hz, "min_required_hz": min_required_hz},
            )
        )
    return issues


def detect_flat_channels(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    thresholds: QualityThresholds | None = None,
) -> list[QualityIssue]:
    """Report channels whose variability is below the flat-line threshold."""
    th = thresholds or QualityThresholds()
    issues: list[QualityIssue] = []
    for i, name in enumerate(channel_names):
        row = signals[i]
        if row.size == 0:
            continue
        finite = row[np.isfinite(row)]
        if finite.size == 0:
            continue
        std = float(np.std(finite))
        if std < th.flat_std:
            issues.append(
                QualityIssue(
                    code="FLAT_CHANNEL",
                    severity=QualitySeverity.WARNING,
                    message="channel is flat (near-zero variability)",
                    channel=name,
                    context={"std": std, "threshold": th.flat_std},
                )
            )
    return issues


def _mains_power_ratio(row: np.ndarray, fs: float, mains_hz: float) -> float:
    finite = row[np.isfinite(row)]
    if finite.size < 4 or fs <= 0 or mains_hz >= fs / 2.0:
        return 0.0
    spectrum = np.abs(np.fft.rfft(finite)) ** 2
    freqs = np.fft.rfftfreq(finite.size, d=1.0 / fs)
    total = float(np.sum(spectrum))
    if total <= 0:
        return 0.0
    band = (freqs >= mains_hz - 1.0) & (freqs <= mains_hz + 1.0)
    return float(np.sum(spectrum[band]) / total)


def detect_noise_issues(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    sampling_rate_hz: float,
    thresholds: QualityThresholds | None = None,
) -> list[QualityIssue]:
    """Report excessive amplitude or dominant mains-frequency power per channel."""
    th = thresholds or QualityThresholds()
    issues: list[QualityIssue] = []
    for i, name in enumerate(channel_names):
        row = signals[i]
        if row.size == 0:
            continue
        finite = row[np.isfinite(row)]
        if finite.size == 0:
            continue
        max_abs = float(np.max(np.abs(finite)))
        if max_abs > th.amplitude_uv:
            issues.append(
                QualityIssue(
                    code="HIGH_AMPLITUDE",
                    severity=QualitySeverity.WARNING,
                    message="channel exceeds the plausible amplitude threshold",
                    channel=name,
                    context={"max_abs": max_abs, "threshold": th.amplitude_uv},
                )
            )
        ratio = _mains_power_ratio(finite, sampling_rate_hz, th.mains_hz)
        if ratio > th.mains_ratio:
            issues.append(
                QualityIssue(
                    code="LINE_NOISE",
                    severity=QualitySeverity.WARNING,
                    message="mains-frequency power dominates the channel spectrum",
                    channel=name,
                    context={"mains_hz": th.mains_hz, "ratio": ratio, "threshold": th.mains_ratio},
                )
            )
    return issues


def _max_constant_run(row: np.ndarray) -> int:
    if row.size == 0:
        return 0
    # Length of the longest run of identical consecutive values.
    change = np.flatnonzero(np.diff(row) != 0)
    if change.size == 0:
        return int(row.size)
    boundaries = np.concatenate(([-1], change, [row.size - 1]))
    return int(np.max(np.diff(boundaries)))


def detect_corrupted_segments(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    thresholds: QualityThresholds | None = None,
) -> list[QualityIssue]:
    """Report non-finite samples and sustained clipping (long constant runs)."""
    th = thresholds or QualityThresholds()
    issues: list[QualityIssue] = []
    for i, name in enumerate(channel_names):
        row = signals[i]
        if row.size == 0:
            continue
        non_finite = int(np.count_nonzero(~np.isfinite(row)))
        if 0 < non_finite < row.size:
            issues.append(
                QualityIssue(
                    code="NONFINITE_SAMPLES",
                    severity=QualitySeverity.CRITICAL,
                    message="channel contains some non-finite samples",
                    channel=name,
                    context={"count": non_finite, "n_samples": int(row.size)},
                )
            )
        finite = row[np.isfinite(row)]
        if finite.size:
            run = _max_constant_run(finite)
            if run >= th.clipping_run:
                issues.append(
                    QualityIssue(
                        code="CLIPPING_RUN",
                        severity=QualitySeverity.WARNING,
                        message="sustained constant run suggests clipping/saturation",
                        channel=name,
                        context={"run_length": run, "threshold": th.clipping_run},
                    )
                )
    return issues
