"""``backend/model_foundation/reports`` — reproducible reports (P4-L).

Builders for the dataset, training, evaluation, experiment, registry, audit, lineage,
validation, and model reports. Each is a deterministic, version-tagged JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_dataset_report, build_training_report, build_evaluation_report,
    build_experiment_report, build_model_report, build_audit_report, build_lineage_report,
    build_validation_report, build_registry_report, build_dataset_registry_report,
)

__all__ = [
    "build_dataset_report", "build_training_report", "build_evaluation_report",
    "build_experiment_report", "build_model_report", "build_audit_report", "build_lineage_report",
    "build_validation_report", "build_registry_report", "build_dataset_registry_report",
]
