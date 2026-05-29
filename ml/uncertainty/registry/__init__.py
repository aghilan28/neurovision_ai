"""``ml/uncertainty/registry`` — the uncertainty registry (V1-P6).

No uncertainty artifact exists outside the registry. Every calibration/conformal/
coverage/risk run is registered with its full version coordinates and lineage id,
mirroring the model registry's governance for the confidence layer.
"""

from __future__ import annotations

from .registry import UncertaintyRecord, UncertaintyRegistry

__all__ = ["UncertaintyRecord", "UncertaintyRegistry"]
