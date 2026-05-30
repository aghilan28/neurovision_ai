"""``backend/inference_foundation/reports`` — reproducible inference reports (P5-L).

Builders for the prediction, confidence, calibration, explainability, registry, audit,
lineage, validation, and inference reports. Each is a deterministic, version-tagged
JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_prediction_report, build_confidence_report, build_calibration_report,
    build_explainability_report, build_inference_report, build_audit_report,
    build_lineage_report, build_validation_report, build_registry_report,
)

__all__ = [
    "build_prediction_report", "build_confidence_report", "build_calibration_report",
    "build_explainability_report", "build_inference_report", "build_audit_report",
    "build_lineage_report", "build_validation_report", "build_registry_report",
]
