"""``backend/real_model_training/benchmarking`` — Benchmark Program (T2-F).

Benchmarks a trained model on the real dataset by REUSING the existing
``backend.production_models`` benchmarker. Deterministic metrics (accuracy / precision /
recall / f1 / ROC-AUC / PR-AUC / ECE / Brier) enter the signature; performance measures
(latency / memory / training-time / inference-time) are informational and never hashed.
"""

from __future__ import annotations

from backend.production_models.benchmarking import benchmark_model

from ..identity import mint  # noqa: F401  (kept for symmetry; benchmark id is reused)
from ..models.domain import Architecture, BenchmarkSummaryRecord
from ..version import DETERMINISTIC_EPOCH

_PROD = __import__("backend.production_models.models.domain", fromlist=["ProductionArchitecture"])
ProductionArchitecture = _PROD.ProductionArchitecture


def benchmark(model, bundle, *, model_id: str, architecture: Architecture, n_classes: int = 2,
              training_time_ms: float = 0.0, split: str = "test",
              created_at: str = DETERMINISTIC_EPOCH) -> BenchmarkSummaryRecord:
    """Benchmark ``model`` on the dataset; return the Track-2 benchmark projection."""
    rec = benchmark_model(model, bundle, model_id=model_id,
                          architecture=ProductionArchitecture(architecture.value),
                          n_classes=n_classes, training_time_ms=training_time_ms, split=split,
                          created_at=created_at)
    return BenchmarkSummaryRecord(
        benchmark_id=rec.benchmark_id, model_id=model_id, architecture=architecture,
        dataset_id=rec.dataset_id, split=rec.split,
        deterministic_metrics=dict(rec.deterministic_metrics), performance=dict(rec.performance),
        n_samples=rec.n_samples, n_classes=rec.n_classes, created_at=created_at)


__all__ = ["benchmark"]
