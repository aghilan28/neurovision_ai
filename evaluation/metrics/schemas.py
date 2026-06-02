"""Schemas for metric definitions and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricKind(str, Enum):
    """Category of a metric."""

    CLASSIFICATION = "classification"
    RANKING = "ranking"
    CONFUSION = "confusion"
    CALIBRATION = "calibration"  # placeholder family in V1
    CLINICAL = "clinical"  # placeholder family in V1


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """Static metadata describing a metric (registered in the metric registry)."""

    name: str
    kind: MetricKind
    version: str
    description: str
    inputs: tuple[str, ...]  # e.g. ("y_true", "y_pred") or ("y_true", "y_score")
    output: str  # "scalar" | "per_class" | "matrix"
    value_range: tuple[float, float] | None = None
    higher_is_better: bool = True
    placeholder: bool = False  # True => registered but not computed in V1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "version": self.version,
            "description": self.description,
            "inputs": list(self.inputs),
            "output": self.output,
            "value_range": list(self.value_range) if self.value_range else None,
            "higher_is_better": self.higher_is_better,
            "placeholder": self.placeholder,
        }


@dataclass(frozen=True, slots=True)
class MetricResult:
    """A computed metric value plus full provenance (metric lineage)."""

    name: str
    kind: MetricKind
    version: str
    value: float | None
    values: dict[str, Any] | None
    n_samples: int
    inputs_fingerprint: str
    scope: str = "binary"  # "binary" | "multiclass"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "version": self.version,
            "value": self.value,
            "values": self.values,
            "n_samples": self.n_samples,
            "inputs_fingerprint": self.inputs_fingerprint,
            "scope": self.scope,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricResult:
        return cls(
            name=data["name"],
            kind=MetricKind(data["kind"]),
            version=data["version"],
            value=data.get("value"),
            values=data.get("values"),
            n_samples=int(data["n_samples"]),
            inputs_fingerprint=data["inputs_fingerprint"],
            scope=data.get("scope", "binary"),
            extra=dict(data.get("extra", {})),
        )
