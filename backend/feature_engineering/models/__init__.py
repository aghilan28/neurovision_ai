"""``backend/feature_engineering/models`` — feature entities + closed vocabularies.

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
numeric extraction. See ``domain.py`` for the canonical definitions.
"""

from __future__ import annotations

from .domain import (
    # closed vocabularies
    FeatureFamily, FeatureGroup, FeatureScope, FrequencyBand, FeatureAssetStatus,
    FeatureValidationSeverity,
    # entities
    FeatureIdentity, FeatureVector, FeatureGroupRecord, FeatureMetadata,
    FeatureValidationRecord, FeatureAuditRecord, FeatureLineageRecord, FeatureVersion,
    FeatureRegistryRecord, FeatureRecord,
)

__all__ = [
    "FeatureFamily", "FeatureGroup", "FeatureScope", "FrequencyBand", "FeatureAssetStatus",
    "FeatureValidationSeverity",
    "FeatureIdentity", "FeatureVector", "FeatureGroupRecord", "FeatureMetadata",
    "FeatureValidationRecord", "FeatureAuditRecord", "FeatureLineageRecord", "FeatureVersion",
    "FeatureRegistryRecord", "FeatureRecord",
]
