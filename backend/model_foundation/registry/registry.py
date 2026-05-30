"""The dataset and model registries (P4-D / P4-I).

No dataset or model exists outside its registry. Re-registering the *same*
``(id, version)`` with a *different* content signature is rejected (silent overwrite
forbidden). Mirrors the platform registry pattern (NR-6).
"""

from __future__ import annotations

from ..version import MODEL_DATASET_VERSION, MODEL_REGISTRY_VERSION
from ..models.domain import DatasetRecord, ModelRegistryRecord


class DatasetRegistry:
    """In-memory dataset registry keyed by ``dataset_id``."""

    def __init__(self) -> None:
        self._records: dict[str, DatasetRecord] = {}
        self._sigs: dict[str, str] = {}

    def register(self, record: DatasetRecord) -> DatasetRecord:
        sig = record.signature()
        if record.dataset_id in self._sigs and self._sigs[record.dataset_id] != sig:
            raise ValueError(
                f"dataset {record.dataset_id} already registered with different content "
                "(silent overwrite forbidden)")
        self._sigs[record.dataset_id] = sig
        self._records[record.dataset_id] = record
        return record

    def get(self, dataset_id: str) -> DatasetRecord:
        if dataset_id not in self._records:
            raise KeyError(f"dataset {dataset_id!r} not in registry")
        return self._records[dataset_id]

    def exists(self, dataset_id: str) -> bool:
        return dataset_id in self._records

    def list_datasets(self) -> list[str]:
        return sorted(self._records)

    def by_source(self, source: str) -> list[str]:
        return sorted(d for d, r in self._records.items() if r.source.value == source)

    def to_dict(self) -> dict:
        return {
            "dataset_registry_version": MODEL_DATASET_VERSION, "n_datasets": len(self._records),
            "datasets": {d: r.to_dict() for d, r in sorted(self._records.items())},
        }


class ModelRegistry:
    """In-memory model registry keyed by ``model_id`` (no orphan models)."""

    def __init__(self) -> None:
        self._records: dict[str, ModelRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: ModelRegistryRecord) -> ModelRegistryRecord:
        key = (record.model_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"model {record.model_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.model_id] = record
        return record

    def get(self, model_id: str) -> ModelRegistryRecord:
        if model_id not in self._records:
            raise KeyError(f"model {model_id!r} not in registry")
        return self._records[model_id]

    def exists(self, model_id: str) -> bool:
        return model_id in self._records

    def list_models(self) -> list[str]:
        return sorted(self._records)

    def by_dataset(self, dataset_id: str) -> list[str]:
        return sorted(m for m, r in self._records.items() if r.dataset_id == dataset_id)

    def by_architecture(self, architecture: str) -> list[str]:
        return sorted(m for m, r in self._records.items() if r.architecture == architecture)

    def by_experiment(self, experiment_id: str) -> list[str]:
        return sorted(m for m, r in self._records.items() if r.experiment_id == experiment_id)

    def to_dict(self) -> dict:
        return {
            "model_registry_version": MODEL_REGISTRY_VERSION, "n_models": len(self._records),
            "models": {m: r.to_dict() for m, r in sorted(self._records.items())},
        }
