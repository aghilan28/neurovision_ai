"""``backend/inference_foundation/lineage`` — inference lineage on the shared tracker (P5-J).

Builds content-addressed prediction lineage nodes on top of ``ml.lineage`` (parenting
both the model node and the input feature node) and re-exports the shared
``LineageTracker``/``LineageRecord`` so prediction nodes live in the same graph as every
upstream node — giving Patient -> ... -> Model -> Prediction complete traceability.
"""

from __future__ import annotations

from .lineage import inference_version_bundle, make_prediction_lineage

from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "inference_version_bundle", "make_prediction_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
