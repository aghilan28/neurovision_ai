"""Benchmark-record construction with mandatory provenance."""

from __future__ import annotations

from collections.abc import Mapping

from evaluation._provenance import VersionBundle
from evaluation.benchmarking.schemas import BenchmarkRecord
from evaluation.metrics.schemas import MetricResult

#: Version of the benchmark-record format.
BENCHMARK_VERSION = "1.0.0"


class BenchmarkProvenanceError(ValueError):
    """Raised when a benchmark would be recorded without required provenance."""


def build_benchmark_record(
    versions: VersionBundle,
    metric_results: Mapping[str, MetricResult],
    *,
    split_fingerprint: str,
    dataset_fingerprint: str | None = None,
    created_at: str | None = None,
    require_model: bool = False,
) -> BenchmarkRecord:
    """Build a :class:`BenchmarkRecord`, refusing to proceed without provenance.

    Required (NR-10/NR-11): dataset_version, split_id, preprocessing_version,
    metrics_version (and a non-empty ``split_fingerprint``). ``model_version`` is
    optional in V1 unless ``require_model`` is set.
    """
    missing = list(versions.missing_required(require_model=require_model))
    if not split_fingerprint:
        missing.append("split_fingerprint")
    if missing:
        raise BenchmarkProvenanceError(
            f"cannot record a benchmark without provenance; missing: {missing}"
        )

    metrics = {name: result.to_dict() for name, result in metric_results.items()}
    return BenchmarkRecord(
        benchmark_version=BENCHMARK_VERSION,
        versions=versions,
        metrics=metrics,
        split_fingerprint=split_fingerprint,
        dataset_fingerprint=dataset_fingerprint,
        created_at=created_at,
    )
