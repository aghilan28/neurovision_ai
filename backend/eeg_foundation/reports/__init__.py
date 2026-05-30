"""``backend/eeg_foundation/reports`` — reproducible EEG reports (P1-H).

Builders for the EEG summary, metadata, validation, audit, lineage, and registry
reports. Each is a deterministic, version-tagged JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_eeg_summary_report,
    build_eeg_metadata_report,
    build_eeg_validation_report,
    build_eeg_audit_report,
    build_eeg_lineage_report,
    build_eeg_registry_report,
)

__all__ = [
    "build_eeg_summary_report",
    "build_eeg_metadata_report",
    "build_eeg_validation_report",
    "build_eeg_audit_report",
    "build_eeg_lineage_report",
    "build_eeg_registry_report",
]
