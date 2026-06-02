"""Enumerations used across the EEG data foundation.

All enums are string-valued so they serialize to stable, human-readable tokens in
canonical JSON (deterministic, diff-friendly, reproducible — AP-6/NR-10).
"""

from __future__ import annotations

from enum import Enum


class FileFormat(str, Enum):
    """Recognized EEG container formats.

    Version 1 supports **EDF and EDF+ only** (V1 directive; NR-13).
    ``UNSUPPORTED`` is a first-class value so the validator can *report* an
    out-of-scope file rather than crash on it.
    """

    EDF = "edf"
    EDF_PLUS_C = "edf+c"  # EDF+ continuous
    EDF_PLUS_D = "edf+d"  # EDF+ discontinuous
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"

    @property
    def is_supported(self) -> bool:
        return self in (FileFormat.EDF, FileFormat.EDF_PLUS_C, FileFormat.EDF_PLUS_D)


class ChannelType(str, Enum):
    """Coarse, deterministic classification of a signal channel.

    Derived from channel labels/dimensions during metadata extraction. This is a
    *technical* categorization (not a clinical one) used for validation and for
    distinguishing data channels from the EDF+ annotation channel.
    """

    EEG = "eeg"
    EOG = "eog"
    ECG = "ecg"
    EMG = "emg"
    REFERENCE = "reference"
    ANNOTATION = "annotation"
    OTHER = "other"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    """Severity of a single validation finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationStatus(str, Enum):
    """Overall outcome of a validation run."""

    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"

    @property
    def is_acceptable(self) -> bool:
        """True when the record may proceed in the lifecycle (no ERROR findings)."""
        return self in (ValidationStatus.PASSED, ValidationStatus.PASSED_WITH_WARNINGS)


class RecordStatus(str, Enum):
    """Lifecycle state of a single EEG record.

    The deterministic lifecycle (Project directive): a file is ``INGESTED``, then
    ``VALIDATED`` (or ``QUARANTINED`` on failure), then becomes part of a dataset
    (``REGISTERED``). ``DEPRECATED`` records are retained for traceability but not
    used by downstream consumers.
    """

    INGESTED = "ingested"
    VALIDATED = "validated"
    QUARANTINED = "quarantined"
    REGISTERED = "registered"
    DEPRECATED = "deprecated"


class DatasetStatus(str, Enum):
    """Lifecycle state of a dataset (a versioned collection of records)."""

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class QualityState(str, Enum):
    """Quality posture of a record or dataset.

    The data foundation only *reports* quality; it never silently drops data
    (mirrors the preprocessing quality rule). ``FLAGGED`` means issues were
    reported and require human attention.
    """

    UNKNOWN = "unknown"
    OK = "ok"
    FLAGGED = "flagged"
