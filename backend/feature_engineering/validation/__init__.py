"""``backend/feature_engineering/validation`` — feature validation (P3-K).

``FeatureContentValidator`` runs build-time content checks (completeness / integrity
/ consistency / determinism) persisted in the asset's ``FeatureValidationRecord``;
``FeatureIntegrityValidator`` reuses ``ml.validation.ValidationReport`` to produce the
full eight checks (content + registry/audit/lineage/version) over a finalized asset.
"""

from __future__ import annotations

from .validators import FeatureContentValidator
from .integrity import FeatureIntegrityValidator

__all__ = ["FeatureContentValidator", "FeatureIntegrityValidator"]
