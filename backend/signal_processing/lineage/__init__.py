"""``backend/signal_processing/lineage`` — signal lineage on the shared tracker (P2-I).

Builds content-addressed processed-EEG lineage nodes on top of ``ml.lineage`` and
re-exports the shared ``LineageTracker``/``LineageRecord`` so processed nodes live in
the same graph as Patient/Case/EEG nodes — giving Patient -> Case -> EEG -> Processed
complete traceability.
"""

from __future__ import annotations

from .lineage import signal_version_bundle, make_signal_lineage

from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "signal_version_bundle", "make_signal_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
