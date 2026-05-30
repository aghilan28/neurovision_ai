"""``backend/model_foundation/models`` — model-foundation entities + closed vocabularies.

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
training/evaluation logic. See ``domain.py`` for the canonical definitions.
"""

from __future__ import annotations

from .domain import (
    # closed vocabularies
    ModelArchitecture, DatasetSource, SplitName, DatasetStatus, ModelStatus, ExperimentStatus,
    # entities
    ModelIdentity, DataSplit, DatasetRecord, TrainingRunRecord, EvaluationRecord,
    ExperimentRecord, ModelMetadata, ModelValidationRecord, ModelAuditRecord,
    ModelLineageRecord, ModelVersion, ModelRegistryRecord, ModelRecord,
)

__all__ = [
    "ModelArchitecture", "DatasetSource", "SplitName", "DatasetStatus", "ModelStatus",
    "ExperimentStatus",
    "ModelIdentity", "DataSplit", "DatasetRecord", "TrainingRunRecord", "EvaluationRecord",
    "ExperimentRecord", "ModelMetadata", "ModelValidationRecord", "ModelAuditRecord",
    "ModelLineageRecord", "ModelVersion", "ModelRegistryRecord", "ModelRecord",
]
