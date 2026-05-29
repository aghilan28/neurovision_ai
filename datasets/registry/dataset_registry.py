"""Dataset registry — discoverable, status-tracked datasets.

Tracks each dataset's version, source, status, validation/quality state,
dependencies, owner, and lineage reference (Project directive). Dependencies
between datasets are kept acyclic on insertion so the registry can never describe
a circular derivation (mirrors the platform-wide acyclicity invariant).
"""

from __future__ import annotations

import os
from typing import Any

from datasets._canonical import canonical_json
from datasets.registry.models import RegisteredDataset
from datasets.schemas.enums import DatasetStatus, QualityState, ValidationStatus

#: Schema version of the persisted dataset-registry file.
DATASET_REGISTRY_SCHEMA = "1.0.0"


class RegistryError(ValueError):
    """Raised on an invalid registry operation (duplicate id, cycle, unknown id)."""


class DatasetRegistry:
    """A discoverable index of datasets with status and dependency tracking."""

    def __init__(self) -> None:
        self._datasets: dict[str, RegisteredDataset] = {}

    # --- registration ----------------------------------------------------
    def register_dataset(
        self,
        dataset_id: str,
        *,
        name: str,
        owner: str,
        source: str,
        description: str = "",
        dependencies: tuple[str, ...] = (),
        created_at: str | None = None,
    ) -> RegisteredDataset:
        """Register a new dataset. Rejects duplicate ids and dependency cycles."""
        if dataset_id in self._datasets:
            raise RegistryError(f"dataset {dataset_id!r} is already registered")
        for dep in dependencies:
            if dep == dataset_id:
                raise RegistryError(f"dataset {dataset_id!r} cannot depend on itself")
            if dep not in self._datasets:
                raise RegistryError(f"dependency {dep!r} is not registered")
        entry = RegisteredDataset(
            dataset_id=dataset_id,
            name=name,
            owner=owner,
            source=source,
            description=description,
            dependencies=tuple(sorted(set(dependencies))),
            created_at=created_at,
            updated_at=created_at,
        )
        self._datasets[dataset_id] = entry
        return entry

    def _replace(self, entry: RegisteredDataset, **changes: object) -> RegisteredDataset:
        """Return an updated dataset entry. ``None`` change values are ignored.

        All change values must be JSON-compatible (enum values passed as their
        ``.value`` strings) so the round-trip through ``from_dict`` is exact.
        """
        data = entry.to_dict()
        for key, value in changes.items():
            if value is None:
                continue
            data[key] = value
        updated = RegisteredDataset.from_dict(data)
        self._datasets[entry.dataset_id] = updated
        return updated

    def update_status(
        self, dataset_id: str, status: DatasetStatus, *, updated_at: str | None = None
    ) -> RegisteredDataset:
        entry = self._require(dataset_id)
        return self._replace(entry, status=status.value, updated_at=updated_at)

    def set_states(
        self,
        dataset_id: str,
        *,
        validation_state: ValidationStatus | None = None,
        quality_state: QualityState | None = None,
        updated_at: str | None = None,
    ) -> RegisteredDataset:
        entry = self._require(dataset_id)
        changes: dict[str, object] = {"updated_at": updated_at}
        if validation_state is not None:
            changes["validation_state"] = validation_state.value
        if quality_state is not None:
            changes["quality_state"] = quality_state.value
        return self._replace(entry, **changes)

    def attach_version(
        self,
        dataset_id: str,
        version: str,
        *,
        record_count: int,
        patient_count: int,
        lineage_ref: str | None = None,
        updated_at: str | None = None,
        make_current: bool = True,
    ) -> RegisteredDataset:
        """Append a version to a dataset and (optionally) make it current."""
        entry = self._require(dataset_id)
        versions = tuple(sorted(set(entry.versions) | {version}))
        changes: dict[str, object] = {
            "versions": list(versions),
            "record_count": record_count,
            "patient_count": patient_count,
            "updated_at": updated_at,
        }
        if make_current:
            changes["current_version"] = version
        if lineage_ref is not None:
            changes["lineage_ref"] = lineage_ref
        return self._replace(entry, **changes)

    # --- discovery -------------------------------------------------------
    def __contains__(self, dataset_id: object) -> bool:
        return dataset_id in self._datasets

    def __len__(self) -> int:
        return len(self._datasets)

    def get(self, dataset_id: str) -> RegisteredDataset:
        return self._require(dataset_id)

    def list_datasets(self) -> tuple[RegisteredDataset, ...]:
        return tuple(self._datasets[k] for k in sorted(self._datasets))

    def find_by_owner(self, owner: str) -> tuple[RegisteredDataset, ...]:
        return tuple(d for d in self.list_datasets() if d.owner == owner)

    def find_by_status(self, status: DatasetStatus) -> tuple[RegisteredDataset, ...]:
        return tuple(d for d in self.list_datasets() if d.status is status)

    def dependencies_of(self, dataset_id: str) -> tuple[str, ...]:
        return self._require(dataset_id).dependencies

    def _require(self, dataset_id: str) -> RegisteredDataset:
        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            raise RegistryError(f"unknown dataset {dataset_id!r}") from exc

    # --- persistence -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DATASET_REGISTRY_SCHEMA,
            "datasets": [d.to_dict() for d in self.list_datasets()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetRegistry:
        registry = cls()
        for entry in data.get("datasets", []):
            dataset = RegisteredDataset.from_dict(entry)
            registry._datasets[dataset.dataset_id] = dataset
        return registry

    def save(self, path: str | os.PathLike[str]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(canonical_json(self.to_dict()))

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> DatasetRegistry:
        import json

        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
