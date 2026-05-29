"""``datasets.validation`` — deterministic EDF validation + reporting.

Validation never *fixes* or *drops* data; it produces structured evidence
(:class:`~datasets.schemas.reports.ValidationReport`) about whether a record may
safely proceed in the lifecycle. Each check is an independent, pure function so it
can be unit-tested in isolation and composed by the ingestion pipeline.

Checks implemented (Project directive):
readability · header integrity · channel consistency · sampling-rate consistency ·
missing-channel detection · corrupted-file detection · invalid-metadata detection ·
duplicate-record detection · unsupported-file detection.
"""

from __future__ import annotations

from datasets.validation.report import VALIDATOR_VERSION, build_report
from datasets.validation.validators import (
    ValidationContext,
    run_all_checks,
    validate_channels,
    validate_duplicate,
    validate_format,
    validate_integrity,
    validate_metadata,
    validate_missing_channels,
    validate_sampling,
)

__all__ = [
    "VALIDATOR_VERSION",
    "ValidationContext",
    "build_report",
    "run_all_checks",
    "validate_channels",
    "validate_duplicate",
    "validate_format",
    "validate_integrity",
    "validate_metadata",
    "validate_missing_channels",
    "validate_sampling",
]
