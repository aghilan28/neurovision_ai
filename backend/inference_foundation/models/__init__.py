"""``backend/inference_foundation/models`` — inference entities + closed vocabularies.

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no model
execution. See ``domain.py`` for the canonical definitions.
"""

from __future__ import annotations

from .domain import (
    # closed vocabularies
    ConfidenceLevel, CalibrationQuality, ExplanationMethod, InferenceStatus,
    # entities
    InferenceIdentity, PredictionClass, PredictionScore, PredictionRecord, ConfidenceRecord,
    CalibrationRecord, FeatureContribution, ExplanationRecord, InferenceValidationRecord,
    InferenceAuditRecord, InferenceLineageRecord, PredictionVersion, InferenceRegistryRecord,
    InferenceRecord,
)

__all__ = [
    "ConfidenceLevel", "CalibrationQuality", "ExplanationMethod", "InferenceStatus",
    "InferenceIdentity", "PredictionClass", "PredictionScore", "PredictionRecord", "ConfidenceRecord",
    "CalibrationRecord", "FeatureContribution", "ExplanationRecord", "InferenceValidationRecord",
    "InferenceAuditRecord", "InferenceLineageRecord", "PredictionVersion", "InferenceRegistryRecord",
    "InferenceRecord",
]
