"""Common value objects shared across intelligence reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Single source of truth for findings across the whole evaluation package.
from evaluation._findings import Finding, Severity

__all__ = [
    "CategoryDistribution",
    "Finding",
    "NumericDistribution",
    "Provenance",
    "Severity",
    "SummaryStats",
]


@dataclass(frozen=True, slots=True)
class SummaryStats:
    """Deterministic summary statistics for a numeric quantity."""

    count: int
    total: float
    mean: float
    std: float
    minimum: float
    p25: float
    median: float
    p75: float
    maximum: float

    @classmethod
    def empty(cls) -> SummaryStats:
        return cls(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "total": self.total,
            "mean": self.mean,
            "std": self.std,
            "minimum": self.minimum,
            "p25": self.p25,
            "median": self.median,
            "p75": self.p75,
            "maximum": self.maximum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummaryStats:
        return cls(
            count=int(data["count"]),
            total=float(data["total"]),
            mean=float(data["mean"]),
            std=float(data["std"]),
            minimum=float(data["minimum"]),
            p25=float(data["p25"]),
            median=float(data["median"]),
            p75=float(data["p75"]),
            maximum=float(data["maximum"]),
        )


@dataclass(frozen=True, slots=True)
class NumericDistribution:
    """Summary statistics plus a fixed-edge histogram for a numeric quantity."""

    name: str
    stats: SummaryStats
    histogram_edges: tuple[float, ...] = ()
    histogram_counts: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "stats": self.stats.to_dict(),
            "histogram_edges": list(self.histogram_edges),
            "histogram_counts": list(self.histogram_counts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NumericDistribution:
        return cls(
            name=data["name"],
            stats=SummaryStats.from_dict(data["stats"]),
            histogram_edges=tuple(float(x) for x in data.get("histogram_edges", ())),
            histogram_counts=tuple(int(x) for x in data.get("histogram_counts", ())),
        )


@dataclass(frozen=True, slots=True)
class CategoryDistribution:
    """A categorical distribution: ordered (category, count) pairs + derived stats."""

    name: str
    counts: tuple[tuple[str, int], ...]

    @property
    def total(self) -> int:
        return sum(c for _, c in self.counts)

    @property
    def n_categories(self) -> int:
        return len(self.counts)

    def fractions(self) -> tuple[tuple[str, float], ...]:
        total = self.total
        if total == 0:
            return tuple((k, 0.0) for k, _ in self.counts)
        return tuple((k, v / total) for k, v in self.counts)

    def imbalance_ratio(self) -> float:
        """Max/min count ratio across non-zero categories (1.0 == perfectly balanced)."""
        values = [c for _, c in self.counts if c > 0]
        if len(values) < 2:
            return 1.0 if values else 0.0
        return max(values) / min(values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "counts": [[k, v] for k, v in self.counts],
            "total": self.total,
            "n_categories": self.n_categories,
            "imbalance_ratio": self.imbalance_ratio(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryDistribution:
        return cls(
            name=data["name"],
            counts=tuple((str(k), int(v)) for k, v in data.get("counts", [])),
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    """Provenance block stamped on every intelligence report (traceability, NR-11)."""

    dataset_id: str | None
    dataset_version: str | None
    intelligence_version: str
    input_fingerprint: str
    n_records: int
    generated_at: str | None = None  # caller-supplied; excluded from fingerprints

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "intelligence_version": self.intelligence_version,
            "input_fingerprint": self.input_fingerprint,
            "n_records": self.n_records,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        return cls(
            dataset_id=data.get("dataset_id"),
            dataset_version=data.get("dataset_version"),
            intelligence_version=data["intelligence_version"],
            input_fingerprint=data["input_fingerprint"],
            n_records=int(data["n_records"]),
            generated_at=data.get("generated_at"),
        )
