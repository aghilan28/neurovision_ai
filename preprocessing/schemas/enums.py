"""Enumerations for the preprocessing layer (string-valued for stable serialization)."""

from __future__ import annotations

from enum import Enum


class StageName(str, Enum):
    """The ordered, independently-testable preprocessing stages."""

    INPUT_VALIDATION = "input_validation"
    CHANNEL_VALIDATION = "channel_validation"
    RESAMPLING = "resampling"
    FILTERING = "filtering"
    MONTAGE = "montage"
    NORMALIZATION = "normalization"
    WINDOWING = "windowing"
    OUTPUT_VALIDATION = "output_validation"
    QUALITY = "quality"
    LINEAGE = "lineage"


class StageStatus(str, Enum):
    """Outcome of running a single stage."""

    OK = "ok"
    SKIPPED = "skipped"
    WARNING = "warning"
    FAILED = "failed"


class NormalizationMethod(str, Enum):
    """Supported, documented normalization methods (no hidden steps)."""

    NONE = "none"
    ZSCORE = "zscore"  # (x - mean) / std
    ROBUST = "robust"  # (x - median) / IQR


class NormalizationScope(str, Enum):
    """Over what axis/extent normalization statistics are computed."""

    PER_CHANNEL_RECORDING = "per_channel_recording"  # stats per channel over the whole recording
    PER_CHANNEL_WINDOW = "per_channel_window"  # stats per channel within each window


class MontageType(str, Enum):
    """Supported montage families (extensible; future types documented, not built)."""

    REFERENTIAL = "referential"  # identity or re-reference to a named electrode
    AVERAGE_REFERENCE = "average_reference"  # common average reference (CAR)
    BIPOLAR = "bipolar"  # derived anode-cathode pairs


class MissingChannelPolicy(str, Enum):
    """How montage application reacts to required channels being absent."""

    ERROR = "error"  # abort with a structured error
    SKIP = "skip"  # skip derivations that need missing channels, report them


class BoundaryPolicy(str, Enum):
    """How windowing treats a trailing partial window."""

    DROP = "drop"  # discard the trailing partial window (default; deterministic length)
    PAD = "pad"  # zero-pad the trailing window to full length


class FilterKind(str, Enum):
    """Filter families implemented in V1."""

    BANDPASS = "bandpass"
    NOTCH = "notch"
    DETREND = "detrend"


class QualitySeverity(str, Enum):
    """Severity of a signal-quality finding (report-only; never removes data)."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
