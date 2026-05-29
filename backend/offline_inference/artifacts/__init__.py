"""``backend/offline_inference/artifacts`` — inference artifact persistence (V1-P7).

Thin, governed wrapper over ``ml.artifacts.ArtifactStore`` (deterministic,
checksummed) specialized for inference artifacts: predictions, calibration,
coverage, risk, clinical outputs, reports, and audit records. No silent
modification — every artifact is sha256-checksummed and listed in a manifest.
"""

from __future__ import annotations

from .store import InferenceArtifactStore, verify_directory

__all__ = ["InferenceArtifactStore", "verify_directory"]
