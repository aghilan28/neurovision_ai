"""``backend/eeg_foundation/registry`` — the EEG asset registry (P1-F).

No EEG asset exists outside the registry. Tracks asset, format, status, validation
state, storage state, metadata state, audit references, and lineage references.
Silent overwrite of the same version with different content is rejected.
"""

from __future__ import annotations

from .registry import EEGRegistry

__all__ = ["EEGRegistry"]
