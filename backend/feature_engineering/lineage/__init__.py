"""``backend/feature_engineering/lineage`` — feature lineage on the shared tracker (P3-J).

Builds content-addressed feature lineage nodes on top of ``ml.lineage`` and
re-exports the shared ``LineageTracker``/``LineageRecord`` so feature nodes live in
the same graph as Patient/Case/EEG/Processed nodes — giving
Patient -> Case -> EEG -> Processed -> Feature complete traceability.
"""

from __future__ import annotations

from .lineage import feature_version_bundle, make_feature_lineage

from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "feature_version_bundle", "make_feature_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
