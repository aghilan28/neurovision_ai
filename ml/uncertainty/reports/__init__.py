"""``ml/uncertainty/reports`` — reproducible uncertainty reports (V1-P6).

Builders for the calibration, coverage, conformal, risk, summary and audit
reports. All reports are plain JSON-able dicts tagged with their producing
versions and lineage id, so they are reproducible and auditable.
"""

from __future__ import annotations

from .reports import (
    build_calibration_report,
    build_conformal_report,
    build_coverage_report,
    build_risk_report,
    build_summary_report,
    build_audit_report,
)

__all__ = [
    "build_calibration_report",
    "build_conformal_report",
    "build_coverage_report",
    "build_risk_report",
    "build_summary_report",
    "build_audit_report",
]
