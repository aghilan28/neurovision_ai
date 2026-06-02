"""Shared evaluation provenance primitive: the :class:`VersionBundle`.

Every benchmark, registry entry, and lineage record references the **complete set
of versions** that produced a result: dataset (+version), split (+generator
version), preprocessing version, metrics version, evaluation version, and a
(future) model version. This is the backbone of "no benchmark without provenance"
and "every metric traceable" (AP-5/AP-6, NR-10/NR-11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evaluation._canonical import canonical_fingerprint


@dataclass(frozen=True, slots=True)
class VersionBundle:
    """The full version provenance of an evaluation result."""

    evaluation_version: str
    dataset_id: str | None = None
    dataset_version: str | None = None
    split_id: str | None = None
    split_generator_version: str | None = None
    preprocessing_version: str | None = None
    metrics_version: str | None = None
    model_version: str | None = None  # reserved for the future modelling phase

    #: Provenance fields required before a benchmark may be recorded.
    REQUIRED = ("dataset_version", "split_id", "preprocessing_version", "metrics_version")

    def missing_required(self, *, require_model: bool = False) -> tuple[str, ...]:
        missing = [name for name in self.REQUIRED if getattr(self, name) in (None, "")]
        if require_model and not self.model_version:
            missing.append("model_version")
        return tuple(missing)

    @property
    def fingerprint(self) -> str:
        return canonical_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_version": self.evaluation_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "split_id": self.split_id,
            "split_generator_version": self.split_generator_version,
            "preprocessing_version": self.preprocessing_version,
            "metrics_version": self.metrics_version,
            "model_version": self.model_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionBundle:
        return cls(
            evaluation_version=data["evaluation_version"],
            dataset_id=data.get("dataset_id"),
            dataset_version=data.get("dataset_version"),
            split_id=data.get("split_id"),
            split_generator_version=data.get("split_generator_version"),
            preprocessing_version=data.get("preprocessing_version"),
            metrics_version=data.get("metrics_version"),
            model_version=data.get("model_version"),
        )
