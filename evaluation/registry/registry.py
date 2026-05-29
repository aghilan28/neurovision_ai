"""Evaluation run registry (discoverable, JSON-backed, deterministic)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from evaluation._canonical import canonical_json
from evaluation._provenance import VersionBundle

#: Schema version of the persisted evaluation-registry file.
EVALUATION_REGISTRY_SCHEMA = "1.0.0"


class RegistryError(ValueError):
    """Raised on an invalid registry operation (duplicate/unknown run)."""


@dataclass(frozen=True, slots=True)
class RegisteredEvaluation:
    """An index entry summarizing one evaluation run."""

    run_id: str
    evaluation_version: str
    versions: VersionBundle
    split_id: str | None
    metric_names: tuple[str, ...]
    result_fingerprint: str
    approved: bool
    artifacts: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    status: str = "recorded"
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "evaluation_version": self.evaluation_version,
            "versions": self.versions.to_dict(),
            "split_id": self.split_id,
            "metric_names": list(self.metric_names),
            "result_fingerprint": self.result_fingerprint,
            "approved": self.approved,
            "artifacts": list(self.artifacts),
            "dependencies": list(self.dependencies),
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisteredEvaluation:
        return cls(
            run_id=data["run_id"],
            evaluation_version=data["evaluation_version"],
            versions=VersionBundle.from_dict(data["versions"]),
            split_id=data.get("split_id"),
            metric_names=tuple(data.get("metric_names", ())),
            result_fingerprint=data["result_fingerprint"],
            approved=bool(data["approved"]),
            artifacts=tuple(data.get("artifacts", ())),
            dependencies=tuple(data.get("dependencies", ())),
            status=data.get("status", "recorded"),
            created_at=data.get("created_at"),
        )


class EvaluationRegistry:
    """An append/update index of evaluation runs, discoverable by id/dataset/split."""

    def __init__(self) -> None:
        self._runs: dict[str, RegisteredEvaluation] = {}

    def __contains__(self, run_id: object) -> bool:
        return run_id in self._runs

    def __len__(self) -> int:
        return len(self._runs)

    def register(self, entry: RegisteredEvaluation, *, allow_replace: bool = False) -> RegisteredEvaluation:
        if entry.run_id in self._runs and not allow_replace:
            raise RegistryError(f"evaluation run {entry.run_id!r} already registered")
        self._runs[entry.run_id] = entry
        return entry

    def get(self, run_id: str) -> RegisteredEvaluation:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise RegistryError(f"unknown evaluation run {run_id!r}") from exc

    def runs(self) -> tuple[RegisteredEvaluation, ...]:
        return tuple(self._runs[k] for k in sorted(self._runs))

    def find_by_dataset(self, dataset_id: str) -> tuple[RegisteredEvaluation, ...]:
        return tuple(r for r in self.runs() if r.versions.dataset_id == dataset_id)

    def find_by_split(self, split_id: str) -> tuple[RegisteredEvaluation, ...]:
        return tuple(r for r in self.runs() if r.split_id == split_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": EVALUATION_REGISTRY_SCHEMA,
            "runs": [r.to_dict() for r in self.runs()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationRegistry:
        registry = cls()
        for entry in data.get("runs", []):
            registry.register(RegisteredEvaluation.from_dict(entry), allow_replace=True)
        return registry

    def save(self, path: str | os.PathLike[str]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(canonical_json(self.to_dict()))

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> EvaluationRegistry:
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
