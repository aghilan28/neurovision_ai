"""``backend/model_foundation/lineage`` — model lineage on the shared tracker (P4-J).

Builds content-addressed dataset / training-run / evaluation / model lineage nodes on
top of ``ml.lineage`` and re-exports the shared ``LineageTracker``/``LineageRecord`` so
model nodes live in the same graph as every upstream node — giving
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model
complete traceability.
"""

from __future__ import annotations

from .lineage import (
    model_version_bundle, make_dataset_lineage, make_training_lineage,
    make_evaluation_lineage, make_model_lineage,
)

from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "model_version_bundle", "make_dataset_lineage", "make_training_lineage",
    "make_evaluation_lineage", "make_model_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
