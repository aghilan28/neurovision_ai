"""The model registry: governed, versioned, traceable model records.

Tracks exactly the fields the directive mandates:
  Model Name · Model Version · Architecture Version · Training Version ·
  Dataset Version · Preprocessing Version · Evaluation Version · Benchmark Version ·
  Artifact Version · Lineage ID · Training Date · Owner · Status.

Governance rules enforced here:
  * No anonymous models — every model is registered before it can be benchmarked.
  * No silent overwrite — re-registering the same model_version must carry an
    identical content signature, else it is rejected (NR-2 / NR-5 spirit).
  * Status transitions are explicit and ordered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..version import REGISTRY_VERSION, ARTIFACT_VERSION, DETERMINISTIC_EPOCH
from ..provenance import hash_obj


class ModelStatus(str, Enum):
    DRAFT = "draft"
    TRAINED = "trained"
    EVALUATED = "evaluated"
    BENCHMARKED = "benchmarked"
    REGISTERED = "registered"
    ARCHIVED = "archived"


# allowed forward transitions (a model may also be archived from any state)
_ALLOWED = {
    ModelStatus.DRAFT: {ModelStatus.TRAINED, ModelStatus.ARCHIVED},
    ModelStatus.TRAINED: {ModelStatus.EVALUATED, ModelStatus.ARCHIVED},
    ModelStatus.EVALUATED: {ModelStatus.BENCHMARKED, ModelStatus.ARCHIVED},
    ModelStatus.BENCHMARKED: {ModelStatus.REGISTERED, ModelStatus.ARCHIVED},
    ModelStatus.REGISTERED: {ModelStatus.ARCHIVED},
    ModelStatus.ARCHIVED: set(),
}


@dataclass
class ModelRecord:
    """A single registry entry (mutable only via governed registry methods)."""

    model_name: str
    model_version: str
    architecture_version: str
    training_version: str
    dataset_version: str
    preprocessing_version: str
    lineage_id: str
    owner: str
    status: ModelStatus = ModelStatus.TRAINED
    evaluation_version: Optional[str] = None
    benchmark_version: Optional[str] = None
    artifact_version: str = ARTIFACT_VERSION
    weights_signature: Optional[str] = None
    training_date: str = DETERMINISTIC_EPOCH
    config_signature: Optional[str] = None
    notes: str = ""

    def content_signature(self) -> str:
        """Hash of the *immutable* identity of this model (excludes mutable status)."""
        return hash_obj(
            {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "architecture_version": self.architecture_version,
                "training_version": self.training_version,
                "dataset_version": self.dataset_version,
                "preprocessing_version": self.preprocessing_version,
                "weights_signature": self.weights_signature,
                "config_signature": self.config_signature,
            }
        )

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "architecture_version": self.architecture_version,
            "training_version": self.training_version,
            "dataset_version": self.dataset_version,
            "preprocessing_version": self.preprocessing_version,
            "evaluation_version": self.evaluation_version,
            "benchmark_version": self.benchmark_version,
            "artifact_version": self.artifact_version,
            "lineage_id": self.lineage_id,
            "training_date": self.training_date,
            "owner": self.owner,
            "status": self.status.value,
            "weights_signature": self.weights_signature,
            "config_signature": self.config_signature,
            "content_signature": self.content_signature(),
            "notes": self.notes,
        }


class ModelRegistry:
    """In-memory model registry keyed by ``model_version``."""

    def __init__(self) -> None:
        self._records: dict[str, ModelRecord] = {}

    def register(self, record: ModelRecord) -> ModelRecord:
        """Register a model. Reject silent overwrites with a different signature."""
        existing = self._records.get(record.model_version)
        if existing is not None:
            if existing.content_signature() != record.content_signature():
                raise ValueError(
                    f"model_version {record.model_version!r} already registered with a "
                    "different content signature (silent overwrite forbidden)"
                )
            return existing  # idempotent re-registration of identical content
        self._records[record.model_version] = record
        return record

    def get(self, model_version: str) -> ModelRecord:
        if model_version not in self._records:
            raise KeyError(f"model_version {model_version!r} not in registry")
        return self._records[model_version]

    def exists(self, model_version: str) -> bool:
        return model_version in self._records

    def set_status(self, model_version: str, status: ModelStatus) -> ModelRecord:
        rec = self.get(model_version)
        if status != rec.status and status not in _ALLOWED[rec.status]:
            raise ValueError(f"illegal status transition {rec.status.value} -> {status.value}")
        rec.status = status
        return rec

    def attach_evaluation(self, model_version: str, evaluation_version: str) -> ModelRecord:
        rec = self.get(model_version)
        rec.evaluation_version = evaluation_version
        return rec

    def attach_benchmark(self, model_version: str, benchmark_version: str) -> ModelRecord:
        rec = self.get(model_version)
        rec.benchmark_version = benchmark_version
        return rec

    def list_models(self) -> list[str]:
        return sorted(self._records)

    def to_dict(self) -> dict:
        return {
            "registry_version": REGISTRY_VERSION,
            "n_models": len(self._records),
            "models": {mv: r.to_dict() for mv, r in sorted(self._records.items())},
        }
