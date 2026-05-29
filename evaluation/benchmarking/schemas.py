"""Benchmark record schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation._canonical import canonical_fingerprint, mint_id
from evaluation._provenance import VersionBundle


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    """A fully-provenanced benchmark result.

    ``metrics`` maps metric name -> the serialized
    :class:`~evaluation.metrics.schemas.MetricResult` dict. ``model_version`` is
    typically ``None`` in V1 (no models yet) — the record still captures the
    dataset/split/preprocessing/metric provenance so future model results slot in
    without reshaping.
    """

    benchmark_version: str
    versions: VersionBundle
    metrics: dict[str, Any]
    split_fingerprint: str
    dataset_fingerprint: str | None = None
    created_at: str | None = None  # provenance only; excluded from fingerprint
    extra: dict[str, Any] = field(default_factory=dict)

    def _fingerprint_payload(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "versions": self.versions.to_dict(),
            "metrics": self.metrics,
            "split_fingerprint": self.split_fingerprint,
            "dataset_fingerprint": self.dataset_fingerprint,
        }

    @property
    def content_fingerprint(self) -> str:
        return canonical_fingerprint(self._fingerprint_payload())

    @property
    def benchmark_id(self) -> str:
        return mint_id("bench", self.content_fingerprint)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "versions": self.versions.to_dict(),
            "metrics": self.metrics,
            "split_fingerprint": self.split_fingerprint,
            "dataset_fingerprint": self.dataset_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "created_at": self.created_at,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkRecord:
        return cls(
            benchmark_version=data["benchmark_version"],
            versions=VersionBundle.from_dict(data["versions"]),
            metrics=dict(data.get("metrics", {})),
            split_fingerprint=data["split_fingerprint"],
            dataset_fingerprint=data.get("dataset_fingerprint"),
            created_at=data.get("created_at"),
            extra=dict(data.get("extra", {})),
        )
