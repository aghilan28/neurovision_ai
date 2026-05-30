"""``backend/inference_foundation/registry`` — the inference (prediction) registry (P5-I).

No prediction asset exists outside the registry; it tracks predictions, confidence,
calibration, explanation records, and audit + lineage references. Silent overwrite of
a version with different content is rejected.
"""

from __future__ import annotations

from .registry import InferenceRegistry

__all__ = ["InferenceRegistry"]
