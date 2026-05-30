"""``backend/feature_engineering/registry`` — the feature-asset registry (P3-I).

No feature asset exists outside the registry; it tracks feature assets, families,
versions, metadata, and audit + lineage references. Silent overwrite of a version
with different content is rejected.
"""

from __future__ import annotations

from .registry import FeatureRegistry

__all__ = ["FeatureRegistry"]
