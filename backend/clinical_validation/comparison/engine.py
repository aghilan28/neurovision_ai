"""Clinical comparison engine (DRP6-F).

Compares >= 2 benchmarked models objectively — ranking, best-per-metric, and a recommended
model — deterministically (ties broken by ``model_id``). Operates over the clinical
:class:`BenchmarkRecord` metric set.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import ComparisonRecord

_COMPARISON_METRICS = ("accuracy", "f1", "roc_auc", "pr_auc", "sensitivity", "specificity")


class ComparisonError(ValueError):
    """Raised when fewer than two benchmarks are supplied."""


def build_comparison(benchmarks) -> ComparisonRecord:
    rows = [{"model_id": b.model_id, "architecture": b.architecture,
             "metrics": {m: float(b.deterministic_metrics.get(m, 0.0)) for m in _COMPARISON_METRICS}}
            for b in benchmarks]
    if len(rows) < 2:
        raise ComparisonError("comparison requires >= 2 benchmarks")
    best_per_metric = {}
    for metric in _COMPARISON_METRICS:
        best = max(rows, key=lambda r: (r["metrics"][metric], r["model_id"]))
        best_per_metric[metric] = {"model_id": best["model_id"], "architecture": best["architecture"],
                                   "value": round(best["metrics"][metric], 9)}
    ranking = [r["model_id"] for r in sorted(
        rows, key=lambda r: (-r["metrics"]["f1"], -r["metrics"]["accuracy"],
                             -r["metrics"]["roc_auc"], r["model_id"]))]
    recommended = ranking[0] if ranking else None
    comparison_key = hash_obj({"ranking": ranking, "recommended": recommended,
                               "n_models": len(rows)})
    return ComparisonRecord(
        comparison_id=mint_identity("validation_comparison", {"comparison_key": comparison_key}).id,
        n_models=len(rows), metrics=_COMPARISON_METRICS, ranking=tuple(ranking),
        best_per_metric=best_per_metric, recommended_model=recommended)


__all__ = ["build_comparison", "ComparisonError"]
