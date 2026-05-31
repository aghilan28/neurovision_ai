"""``backend/real_model_training/comparison`` — Model Comparison Engine (T2-G).

Compares >=2 benchmarked models (model vs model, version vs version) by REUSING the
production comparison engine, and projects a deterministic ``ComparisonRecord`` with the
ranking, best-per-metric, and the recommended (selected) model.
"""

from __future__ import annotations

from backend.production_models.evaluation import compare_models

from ..identity import mint
from ..models.domain import ComparisonRecord
from ..version import DETERMINISTIC_EPOCH


def compare(benchmark_records: list, *, dataset_id: str,
            created_at: str = DETERMINISTIC_EPOCH) -> ComparisonRecord:
    """Compare Track-2 benchmark records (duck-typed for the reused comparison engine)."""
    result = compare_models(benchmark_records)
    comparison_id = mint("model_comparison", {
        "dataset_id": dataset_id, "ranking": result["ranking"],
        "recommended": result["recommended_model"]})
    return ComparisonRecord(
        comparison_id=comparison_id, dataset_id=dataset_id, n_models=result["n_models"],
        metrics=tuple(result["metrics"]), ranking=tuple(result["ranking"]),
        best_per_metric=result["best_per_metric"], recommended_model=result["recommended_model"],
        created_at=created_at)


__all__ = ["compare"]
