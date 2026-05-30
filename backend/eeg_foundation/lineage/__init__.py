"""``backend/eeg_foundation/lineage`` — EEG lineage on the shared tracker (P1-G).

Builds content-addressed EEG lineage nodes on top of ``ml.lineage`` (NR-6: reuse,
don't re-implement) and re-exports the shared ``LineageTracker``/``LineageRecord`` so
EEG nodes live in the same graph as Patient/Case nodes — giving
Patient -> Case -> EEG Asset complete traceability.
"""

from __future__ import annotations

from .lineage import eeg_version_bundle, make_eeg_lineage

# Re-export the shared lineage tracker + record type (integration, not a parallel system).
from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "eeg_version_bundle",
    "make_eeg_lineage",
    "LineageTracker",
    "LineageRecord",
    "make_lineage_record",
]
