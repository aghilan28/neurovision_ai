"""``ml/benchmarking`` — benchmark records & registry (V1-P5).

Integrates with the evaluation framework (V1-P4) through a *port* rather than a
code import: ``ml`` must not import ``evaluation`` (NR-8). The evaluation layer
(which is allowed to import ``ml``) computes patient-disjoint metrics and returns
an ``EvaluationResult`` (a contract owned here); the orchestrator (``scripts/``)
then registers a ``BenchmarkRecord``.

Every benchmark record bundles: metrics · dataset · split · version bundle ·
lineage bundle · evaluation audit · benchmark id — and is reproducible.
"""

from __future__ import annotations

from .benchmark import (
    EvaluationResult,
    EvaluationPort,
    BenchmarkRecord,
    BenchmarkRegistry,
    build_benchmark_record,
)

__all__ = [
    "EvaluationResult",
    "EvaluationPort",
    "BenchmarkRecord",
    "BenchmarkRegistry",
    "build_benchmark_record",
]
