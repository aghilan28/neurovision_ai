"""``backend/signal_processing/artifacts`` — artifact detection + removal (P2-E/F).

``ArtifactDetectionEngine`` finds the seven mandated artifact classes (eye-blink,
EMG, movement, powerline, channel dropout, flat/saturated channels) and emits
structured ``SignalArtifactRecord``s. ``ArtifactRemovalEngine`` removes/repairs them
deterministically (ICA, adaptive filtering, interpolation, channel repair, noise
suppression) without ever mutating the raw signal.
"""

from __future__ import annotations

from .detection import ArtifactDetectionEngine
from .removal import ArtifactRemovalEngine

__all__ = ["ArtifactDetectionEngine", "ArtifactRemovalEngine"]
