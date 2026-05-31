"""The production-model registry (DRP2-H).

Tracks the **new** production-candidate artifacts — production models, training
experiments, benchmarks, evaluations, and readiness assessments — that no other
subsystem stores. It integrates with, and does **not** duplicate, the shared
model-foundation ``DatasetRegistry`` + ``ModelRegistry`` (a production model
cross-references the shared dataset id + the registered base-model id).

**No orphan records**: every model entry must reference a lineage node + an audit head,
and its benchmark / evaluation / readiness must be registered. Re-registering the same
``(id, version)`` with different content is rejected (silent overwrite forbidden).
"""

from __future__ import annotations

from ..models.domain import (
    EntityKind, ModelBenchmarkRecord, ModelEvaluationRecord, ModelReadinessRecord,
    ModelRegistryRecord, TrainingExperimentRecord,
)
from ..version import PRODUCTION_REGISTRY_VERSION

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class ProductionModelRegistry:
    """In-memory registry of production-candidate artifacts, keyed by id."""

    version = PRODUCTION_REGISTRY_VERSION

    def __init__(self) -> None:
        self._models: dict[str, ModelRegistryRecord] = {}
        self._experiments: dict[str, TrainingExperimentRecord] = {}
        self._benchmarks: dict[str, ModelBenchmarkRecord] = {}
        self._evaluations: dict[str, ModelEvaluationRecord] = {}
        self._readiness: dict[str, ModelReadinessRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    # --- model registry record ------------------------------------------------
    def register_model(self, record: ModelRegistryRecord) -> ModelRegistryRecord:
        if not record.lineage_id:
            raise RegistryError(f"{record.model_id!r} has no lineage node (orphans forbidden)")
        if not record.audit_state or record.audit_state == GENESIS:
            raise RegistryError(f"{record.model_id!r} has no audit head (orphans forbidden)")
        if not (record.benchmark_id and record.model_evaluation_id and record.readiness_id):
            raise RegistryError(
                f"{record.model_id!r} missing benchmark/evaluation/readiness (orphans forbidden)")
        key = (record.model_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"model {record.model_id} v{record.version} already registered with different content")
        self._version_sigs[key] = sig
        self._models[record.model_id] = record
        return record

    def register_experiment(self, record: TrainingExperimentRecord) -> TrainingExperimentRecord:
        self._experiments[record.experiment_id] = record
        return record

    def register_benchmark(self, record: ModelBenchmarkRecord) -> ModelBenchmarkRecord:
        self._benchmarks[record.benchmark_id] = record
        return record

    def register_evaluation(self, record: ModelEvaluationRecord) -> ModelEvaluationRecord:
        self._evaluations[record.model_evaluation_id] = record
        return record

    def register_readiness(self, record: ModelReadinessRecord) -> ModelReadinessRecord:
        self._readiness[record.readiness_id] = record
        return record

    # --- accessors ------------------------------------------------------------
    def get_model(self, model_id: str) -> ModelRegistryRecord:
        if model_id not in self._models:
            raise KeyError(f"production model {model_id!r} not in registry")
        return self._models[model_id]

    def exists(self, model_id: str) -> bool:
        return model_id in self._models

    def list_models(self) -> list[str]:
        return sorted(self._models)

    def by_architecture(self, architecture: str) -> list[str]:
        return sorted(m for m, r in self._models.items() if r.architecture == architecture)

    def by_dataset(self, dataset_id: str) -> list[str]:
        return sorted(m for m, r in self._models.items() if r.dataset_id == dataset_id)

    def by_readiness(self, classification: str) -> list[str]:
        return sorted(m for m, r in self._models.items()
                      if r.readiness_class.value == classification)

    def counts(self) -> dict:
        return {
            EntityKind.MODEL.value: len(self._models),
            EntityKind.EXPERIMENT.value: len(self._experiments),
            EntityKind.BENCHMARK.value: len(self._benchmarks),
            EntityKind.EVALUATION.value: len(self._evaluations),
            EntityKind.READINESS.value: len(self._readiness),
        }

    def orphans(self) -> list[str]:
        """Model entries whose referenced benchmark/evaluation/readiness are not registered."""
        out = []
        for mid, r in self._models.items():
            if (r.benchmark_id not in self._benchmarks
                    or r.model_evaluation_id not in self._evaluations
                    or r.readiness_id not in self._readiness
                    or not r.lineage_id or not r.audit_state or r.audit_state == GENESIS):
                out.append(mid)
        return sorted(out)

    def to_dict(self) -> dict:
        return {
            "production_model_registry_version": self.version, "counts": self.counts(),
            "models": {m: r.to_dict() for m, r in sorted(self._models.items())},
            "experiments": {e: r.to_dict() for e, r in sorted(self._experiments.items())},
            "benchmarks": {b: r.to_dict() for b, r in sorted(self._benchmarks.items())},
            "evaluations": {e: r.to_dict() for e, r in sorted(self._evaluations.items())},
            "readiness": {r_id: r.to_dict() for r_id, r in sorted(self._readiness.items())},
        }


__all__ = ["ProductionModelRegistry", "RegistryError"]
