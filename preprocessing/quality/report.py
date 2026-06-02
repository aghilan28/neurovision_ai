"""Quality report assembly — runs all detectors and aggregates findings."""

from __future__ import annotations

import numpy as np

from preprocessing.quality.detectors import (
    QUALITY_OP_VERSION,
    QualityThresholds,
    detect_corrupted_segments,
    detect_flat_channels,
    detect_invalid_channels,
    detect_missing_channels,
    detect_noise_issues,
    detect_sampling_issues,
)
from preprocessing.schemas.reports import QualityReport


def assess_quality(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    sampling_rate_hz: float,
    *,
    expected_channels: tuple[str, ...] = (),
    min_required_hz: float = 0.0,
    thresholds: QualityThresholds | None = None,
) -> QualityReport:
    """Run all quality detectors and return an aggregated, deterministic report.

    The report only describes problems; it never modifies ``signals``.
    """
    th = thresholds or QualityThresholds()
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))

    issues = []
    issues += detect_missing_channels(channel_names, expected_channels)
    issues += detect_sampling_issues(sampling_rate_hz, min_required_hz)
    issues += detect_invalid_channels(arr, channel_names)
    issues += detect_flat_channels(arr, channel_names, th)
    issues += detect_noise_issues(arr, channel_names, sampling_rate_hz, th)
    issues += detect_corrupted_segments(arr, channel_names, th)

    checks_run = (
        "missing_channels",
        "sampling",
        "invalid_channels",
        "flat_channels",
        "noise",
        "corrupted_segments",
    )
    return QualityReport(
        issues=tuple(issues),
        checks_run=checks_run,
        quality_version=QUALITY_OP_VERSION,
    )
