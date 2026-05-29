"""``backend/offline_inference/reports`` — reproducible inference reports (V1-P7).

Builders for the inference, calibration, coverage, risk, audit and summary reports.
Each is a plain JSON-able dict tagged with versions and lineage id; the orchestrator
persists them via the checksummed artifact store.
"""

from __future__ import annotations

from .reports import (
    build_inference_report,
    build_calibration_report,
    build_coverage_report,
    build_risk_report,
    build_audit_report,
    build_summary_report,
)

__all__ = [
    "build_inference_report",
    "build_calibration_report",
    "build_coverage_report",
    "build_risk_report",
    "build_audit_report",
    "build_summary_report",
]
