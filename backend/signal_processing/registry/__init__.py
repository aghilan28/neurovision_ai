"""``backend/signal_processing/registry`` — the processed-EEG registry (P2-H).

No processed asset exists outside the registry; it references the raw EEG asset,
quality/artifact/processing records, and audit + lineage references. Silent
overwrite of a version with different content is rejected.
"""

from __future__ import annotations

from .registry import SignalRegistry

__all__ = ["SignalRegistry"]
