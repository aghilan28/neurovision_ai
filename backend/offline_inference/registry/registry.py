"""The inference registry: governed, versioned, traceable inference records.

Tracks exactly the fields the directive mandates:
  Inference ID · Pipeline Version · Dataset Version · Preprocessing Version ·
  Model Version · Evaluation Version · Calibration Version · Conformal Version ·
  Output Version · Artifact Version · Lineage Version.

Re-registering the same Inference ID with different content is rejected (no silent
overwrite); identical re-registration is idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    INFERENCE_REGISTRY_VERSION,
    OUTPUT_CONTRACT_VERSION,
    INFERENCE_ARTIFACT_VERSION,
    INFERENCE_LINEAGE_VERSION,
    DETERMINISTIC_EPOCH,
)


@dataclass
class InferenceRecord:
    """A single inference registry entry."""

    inference_id: str
    pipeline_version: str
    dataset_version: str
    preprocessing_version: str
    model_version: str
    evaluation_version: str
    calibration_version: str
    conformal_version: str
    lineage_id: str
    output_version: str = OUTPUT_CONTRACT_VERSION
    artifact_version: str = INFERENCE_ARTIFACT_VERSION
    lineage_version: str = INFERENCE_LINEAGE_VERSION
    status: str = "completed"
    created_at: str = DETERMINISTIC_EPOCH

    def content_signature(self) -> str:
        return hash_obj({
            "inference_id": self.inference_id,
            "pipeline_version": self.pipeline_version,
            "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version,
            "model_version": self.model_version,
            "evaluation_version": self.evaluation_version,
            "calibration_version": self.calibration_version,
            "conformal_version": self.conformal_version,
            "output_version": self.output_version,
            "artifact_version": self.artifact_version,
            "lineage_version": self.lineage_version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "inference_id": self.inference_id,
            "pipeline_version": self.pipeline_version,
            "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version,
            "model_version": self.model_version,
            "evaluation_version": self.evaluation_version,
            "calibration_version": self.calibration_version,
            "conformal_version": self.conformal_version,
            "output_version": self.output_version,
            "artifact_version": self.artifact_version,
            "lineage_version": self.lineage_version,
            "lineage_id": self.lineage_id,
            "status": self.status,
            "created_at": self.created_at,
            "content_signature": self.content_signature(),
        }


class InferenceRegistry:
    """In-memory inference registry keyed by ``inference_id``."""

    def __init__(self) -> None:
        self._records: dict[str, InferenceRecord] = {}

    def register(self, record: InferenceRecord) -> InferenceRecord:
        existing = self._records.get(record.inference_id)
        if existing is not None:
            if existing.content_signature() != record.content_signature():
                raise ValueError(
                    f"inference_id {record.inference_id!r} already registered with "
                    "different content (silent overwrite forbidden)"
                )
            return existing
        self._records[record.inference_id] = record
        return record

    def get(self, inference_id: str) -> InferenceRecord:
        if inference_id not in self._records:
            raise KeyError(f"inference_id {inference_id!r} not in registry")
        return self._records[inference_id]

    def exists(self, inference_id: str) -> bool:
        return inference_id in self._records

    def list_inferences(self) -> list[str]:
        return sorted(self._records)

    def to_dict(self) -> dict:
        return {
            "inference_registry_version": INFERENCE_REGISTRY_VERSION,
            "n_inferences": len(self._records),
            "inferences": {iid: r.to_dict() for iid, r in sorted(self._records.items())},
        }
