"""Benchmark contracts, records, and registry.

The ``EvaluationResult`` / ``EvaluationPort`` contract is owned by the ML layer so
that the (downstream) evaluation module can produce results in a shape the
benchmark registry understands — without the ML layer ever importing evaluation.
This is the inversion-of-dependency that keeps the DAG acyclic (NR-8): evaluation
imports ml and returns ml-defined results; ml never imports evaluation.

A ``BenchmarkRecord`` is content-addressed (``benchmark_id``) and bundles
everything needed to reproduce and audit a benchmark: metrics, dataset/split
provenance, the full version bundle, the lineage chain, and the evaluation audit
(which must assert patient-disjointness, NR-3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from ..version import BENCHMARK_VERSION, DETERMINISTIC_EPOCH
from ..provenance import content_id


@dataclass(frozen=True)
class EvaluationResult:
    """Result contract returned by the evaluation framework (V1-P4).

    The ``evaluation_audit`` MUST record that the evaluation was patient-disjoint;
    benchmark registration refuses to register a non-patient-disjoint result.
    """

    evaluation_version: str
    metrics: dict                      # overall + macro metrics
    per_class: dict                    # per-class metrics
    evaluation_audit: dict             # patient_disjoint flag, split/dataset versions, assertions
    calibration: Optional[dict] = None  # ece/mce/brier (measured by evaluation)
    coverage: Optional[dict] = None     # conformal coverage (measured by evaluation)

    def is_patient_disjoint(self) -> bool:
        return bool(self.evaluation_audit.get("patient_disjoint", False))

    def to_dict(self) -> dict:
        return {
            "evaluation_version": self.evaluation_version,
            "metrics": self.metrics,
            "per_class": self.per_class,
            "evaluation_audit": self.evaluation_audit,
            "calibration": self.calibration,
            "coverage": self.coverage,
        }


@runtime_checkable
class EvaluationPort(Protocol):
    """The interface the ML layer expects from the evaluation framework.

    Implemented by ``evaluation`` (which may import ml). The ML layer depends only
    on this structural protocol, never on the evaluation module.
    """

    def evaluate(
        self,
        *,
        probabilities: Any,
        labels: Any,
        patient_ids: Any,
        class_names: tuple,
        dataset_version: str,
        split_version: str,
    ) -> EvaluationResult:
        ...


@dataclass(frozen=True)
class BenchmarkRecord:
    """A reproducible, content-addressed benchmark result."""

    benchmark_id: str
    model_name: str
    model_version: str
    metrics: dict
    per_class: dict
    dataset_version: str
    split_summary: dict
    version_bundle: dict
    lineage_bundle: list
    evaluation_version: str
    evaluation_audit: dict
    calibration: Optional[dict] = None
    coverage: Optional[dict] = None
    benchmark_version: str = BENCHMARK_VERSION
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "metrics": self.metrics,
            "per_class": self.per_class,
            "dataset_version": self.dataset_version,
            "split_summary": self.split_summary,
            "version_bundle": self.version_bundle,
            "lineage_bundle": self.lineage_bundle,
            "evaluation_version": self.evaluation_version,
            "evaluation_audit": self.evaluation_audit,
            "calibration": self.calibration,
            "coverage": self.coverage,
            "created_at": self.created_at,
        }


def build_benchmark_record(
    *,
    model_name: str,
    model_version: str,
    evaluation: EvaluationResult,
    dataset_version: str,
    split_summary: Mapping[str, Any],
    version_bundle: Mapping[str, Any],
    lineage_bundle: list,
    created_at: str = DETERMINISTIC_EPOCH,
) -> BenchmarkRecord:
    """Assemble a reproducible benchmark record from an evaluation result.

    Refuses to build a benchmark for a non-patient-disjoint evaluation (NR-3).
    """
    if not evaluation.is_patient_disjoint():
        raise ValueError(
            "refusing to build benchmark: evaluation is not patient-disjoint (NR-3)"
        )
    benchmark_id = content_id(
        "benchmark",
        {
            "model_version": model_version,
            "evaluation_version": evaluation.evaluation_version,
            "dataset_version": dataset_version,
            "split_version": split_summary.get("split_version"),
            "metrics": evaluation.metrics,
            "per_class": evaluation.per_class,
        },
    )
    return BenchmarkRecord(
        benchmark_id=benchmark_id,
        model_name=model_name,
        model_version=model_version,
        metrics=evaluation.metrics,
        per_class=evaluation.per_class,
        dataset_version=dataset_version,
        split_summary=dict(split_summary),
        version_bundle=dict(version_bundle),
        lineage_bundle=list(lineage_bundle),
        evaluation_version=evaluation.evaluation_version,
        evaluation_audit=evaluation.evaluation_audit,
        calibration=evaluation.calibration,
        coverage=evaluation.coverage,
        created_at=created_at,
    )


class BenchmarkRegistry:
    """Registry of benchmark records keyed by ``benchmark_id``."""

    def __init__(self) -> None:
        self._records: dict[str, BenchmarkRecord] = {}

    def register(self, record: BenchmarkRecord) -> BenchmarkRecord:
        existing = self._records.get(record.benchmark_id)
        if existing is not None:
            if existing.to_dict() != record.to_dict():
                raise ValueError(
                    f"benchmark_id {record.benchmark_id!r} already registered with different content"
                )
            return existing
        self._records[record.benchmark_id] = record
        return record

    def get(self, benchmark_id: str) -> BenchmarkRecord:
        if benchmark_id not in self._records:
            raise KeyError(f"unknown benchmark_id {benchmark_id!r}")
        return self._records[benchmark_id]

    def list_benchmarks(self) -> list[str]:
        return sorted(self._records)

    def leaderboard(self, metric: str = "macro_f1") -> list[dict]:
        """Return benchmarks sorted by a metric (future models vs. baselines)."""
        rows = [
            {
                "model_name": r.model_name,
                "model_version": r.model_version,
                "benchmark_id": r.benchmark_id,
                metric: r.metrics.get(metric),
            }
            for r in self._records.values()
        ]
        rows.sort(key=lambda x: (x[metric] is None, -(x[metric] or 0.0)))
        return rows

    def to_dict(self) -> dict:
        return {
            "benchmark_version": BENCHMARK_VERSION,
            "n_benchmarks": len(self._records),
            "benchmarks": {bid: r.to_dict() for bid, r in sorted(self._records.items())},
        }
