"""``backend/inference_foundation/validation`` — inference validation (P5-K).

``InferenceContentValidator`` runs build-time checks (prediction/confidence/calibration/
explanation/determinism) persisted in the asset's ``InferenceValidationRecord``;
``InferenceIntegrityValidator`` reuses ``ml.validation.ValidationReport`` to produce the
full nine checks (content + registry/audit/lineage/version) over a finalized asset.
"""

from __future__ import annotations

from .validators import InferenceContentValidator
from .integrity import InferenceIntegrityValidator

__all__ = ["InferenceContentValidator", "InferenceIntegrityValidator"]
