"""``backend/offline_inference/validation`` — inference validation (V1-P7).

The mandated post-inference integrity checks: version consistency, artifact
integrity, lineage integrity, calibration integrity, coverage integrity, output
integrity, audit integrity. A failing check is stop-and-remediate.
"""

from __future__ import annotations

from .validators import InferenceValidator, InferenceValidationError

__all__ = ["InferenceValidator", "InferenceValidationError"]
