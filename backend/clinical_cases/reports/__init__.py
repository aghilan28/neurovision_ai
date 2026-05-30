"""``backend/clinical_cases/reports`` — reproducible case reports (V2-P1).

Builders for the case summary, audit, lineage, lifecycle, and validation reports.
Each is a plain JSON-able dict tagged with versions; deterministic for a given case
state.
"""

from __future__ import annotations

from .reports import (
    build_case_summary_report,
    build_case_audit_report,
    build_case_lineage_report,
    build_case_lifecycle_report,
    build_case_validation_report,
)

__all__ = [
    "build_case_summary_report",
    "build_case_audit_report",
    "build_case_lineage_report",
    "build_case_lifecycle_report",
    "build_case_validation_report",
]
