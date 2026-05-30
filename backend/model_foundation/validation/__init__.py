"""``backend/model_foundation/validation`` — model validation (P4-K).

``ModelContentValidator`` runs build-time checks (dataset/training/evaluation/model/
determinism) persisted in the model's ``ModelValidationRecord``;
``ModelIntegrityValidator`` reuses ``ml.validation.ValidationReport`` to produce the
full nine checks (content + registry/audit/lineage/version) over a finalized model.
"""

from __future__ import annotations

from .validators import ModelContentValidator
from .integrity import ModelIntegrityValidator

__all__ = ["ModelContentValidator", "ModelIntegrityValidator"]
