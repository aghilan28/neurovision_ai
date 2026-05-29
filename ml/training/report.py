"""Training report builder.

A training report is the human- and machine-readable summary of a run: the model
identity, version coordinates, training history, validation results, lineage id,
and artifact references. It is reproducible (canonical JSON) and pins everything
needed to audit or regenerate the run.
"""

from __future__ import annotations

from typing import Any

from ..version import TRAINING_FRAMEWORK_VERSION


def build_training_report(
    *,
    model_name: str,
    model_version: str,
    architecture_spec: dict,
    version_bundle: dict,
    training_history: dict,
    validation_report: dict,
    lineage_id: str,
    artifacts: dict,
    manifest: dict,
) -> dict:
    return {
        "report_type": "training",
        "training_framework_version": TRAINING_FRAMEWORK_VERSION,
        "model_name": model_name,
        "model_version": model_version,
        "architecture_spec": architecture_spec,
        "version_bundle": version_bundle,
        "training_history": training_history,
        "training_validation": validation_report,
        "lineage_id": lineage_id,
        "artifacts": artifacts,
        "manifest": manifest,
    }
