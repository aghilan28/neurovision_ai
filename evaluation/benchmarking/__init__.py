"""``evaluation.benchmarking`` — provenance-bound benchmark records (V1-P4).

A benchmark result cannot exist without provenance: every
:class:`~evaluation.benchmarking.schemas.BenchmarkRecord` carries the full
:class:`~evaluation._provenance.VersionBundle` (dataset/split/preprocessing/metric
/evaluation/[model] versions). :func:`build_benchmark_record` refuses to produce a
record if required provenance is missing (NR-10/NR-11).
"""

from __future__ import annotations

from evaluation.benchmarking.builder import (
    BENCHMARK_VERSION,
    BenchmarkProvenanceError,
    build_benchmark_record,
)
from evaluation.benchmarking.schemas import BenchmarkRecord

__all__ = [
    "BENCHMARK_VERSION",
    "BenchmarkProvenanceError",
    "BenchmarkRecord",
    "build_benchmark_record",
]
