"""``preprocessing.quality`` — signal quality assessment (report-only).

Detects common EEG signal-quality problems and reports them as structured
findings. **It never removes or alters data** (Project directive): a flagged
channel/segment remains in the output; the decision to act on a flag is made
explicitly downstream.

Detectors: missing channels · invalid (non-finite) channels · sampling issues ·
flat (dead) channels · noise (amplitude / mains) issues · corrupted segments
(non-finite runs, sustained clipping).
"""

from __future__ import annotations

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
from preprocessing.quality.report import assess_quality

__all__ = [
    "QUALITY_OP_VERSION",
    "QualityThresholds",
    "assess_quality",
    "detect_corrupted_segments",
    "detect_flat_channels",
    "detect_invalid_channels",
    "detect_missing_channels",
    "detect_noise_issues",
    "detect_sampling_issues",
]
