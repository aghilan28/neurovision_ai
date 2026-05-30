"""``backend/eeg_foundation/validation`` — EEG validation (P1-C).

Two complementary validators:
  * ``EEGFileValidator`` — file acceptance. Returns structured findings
    (``EEGValidationResult``/``EEGValidationFinding``/severities), never exceptions,
    covering corrupted/unreadable/unsupported files, missing channels, invalid
    sampling rates/durations, and metadata/annotation errors.
  * ``EEGIntegrityValidator`` — asset integrity. Reuses
    ``ml.validation.ValidationReport`` to check that a built asset is identity/
    registry/storage/metadata/audit/lineage/version consistent.
"""

from __future__ import annotations

from .validators import EEGFileValidator
from .integrity import EEGIntegrityValidator, EEGIntegrityError

__all__ = ["EEGFileValidator", "EEGIntegrityValidator", "EEGIntegrityError"]
