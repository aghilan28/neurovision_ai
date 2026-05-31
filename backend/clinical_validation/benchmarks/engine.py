"""Clinical benchmark program (DRP6-C).

Benchmarks every production model (developed via the reused DRP-2 ``ProductionModelService``)
against the available datasets, producing a clinical :class:`BenchmarkRecord` + a
:class:`PerformanceRecord`. It **reuses** the DRP-2 deterministic metrics (accuracy /
precision / recall / F1 / ROC-AUC / PR-AUC / ECE / Brier) and adds **sensitivity** +
**specificity** derived from the DRP-2 evaluation's confusion matrix. Performance measures
(latency / memory / inference + training time) are carried as informational evidence.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import BenchmarkRecord, PerformanceRecord
from ..version import DETERMINISTIC_EPOCH


def sensitivity_specificity(confusion) -> tuple[float, float]:
    """Macro one-vs-rest sensitivity (recall) + specificity from an n x n confusion matrix."""
    cm = [list(row) for row in confusion]
    n = len(cm)
    total = sum(sum(r) for r in cm)
    sens, spec = [], []
    for c in range(n):
        tp = cm[c][c]
        fn = sum(cm[c]) - tp
        fp = sum(cm[r][c] for r in range(n)) - tp
        tn = total - tp - fn - fp
        if (tp + fn) > 0:
            sens.append(tp / (tp + fn))
        if (tn + fp) > 0:
            spec.append(tn / (tn + fp))
    macro_sens = sum(sens) / len(sens) if sens else 0.0
    macro_spec = sum(spec) / len(spec) if spec else 0.0
    return float(macro_sens), float(macro_spec)


def build_benchmark(outcome, *, dataset_label: str,
                    created_at: str = DETERMINISTIC_EPOCH) -> tuple[BenchmarkRecord, PerformanceRecord]:
    """Build the clinical benchmark + performance records from a DRP-2 production outcome."""
    src = outcome.benchmark
    metrics = dict(src.deterministic_metrics)
    sens, spec = sensitivity_specificity(outcome.evaluation.confusion_matrix)
    deterministic_metrics = {
        "accuracy": metrics.get("accuracy", 0.0),
        "precision": metrics.get("precision_macro", 0.0),
        "recall": metrics.get("recall_macro", 0.0),
        "f1": metrics.get("f1_macro", 0.0),
        "roc_auc": metrics.get("roc_auc_macro", 0.0),
        "pr_auc": metrics.get("pr_auc_macro", 0.0),
        "sensitivity": sens,
        "specificity": spec,
        "ece": metrics.get("ece", 0.0),
        "brier": metrics.get("brier", 0.0),
    }
    metrics_key = hash_obj({"model_id": outcome.model.model_id, "dataset_label": dataset_label,
                            "metrics": {k: round(float(v), 9)
                                        for k, v in sorted(deterministic_metrics.items())}})
    benchmark_id = mint_identity("validation_benchmark", {
        "model_id": outcome.model.model_id, "metrics_key": metrics_key}).id
    benchmark = BenchmarkRecord(
        benchmark_id=benchmark_id, model_id=outcome.model.model_id,
        architecture=outcome.architecture.value, dataset_label=dataset_label,
        deterministic_metrics=deterministic_metrics, performance=dict(src.performance),
        n_samples=src.n_samples, n_classes=src.n_classes, source_benchmark_id=src.benchmark_id,
        created_at=created_at)

    # performance_id is content-addressed on the model only (NOT on the wall-clock timings),
    # so it is deterministic; the timing measures are informational and never hashed (NR-9/NR-10).
    perf_key = hash_obj({"model_id": outcome.model.model_id, "kind": "performance"})
    performance = PerformanceRecord(
        performance_id=mint_identity("validation_performance", {
            "model_id": outcome.model.model_id, "perf_key": perf_key}).id,
        model_id=outcome.model.model_id, measures=dict(src.performance))
    return benchmark, performance


__all__ = ["build_benchmark", "sensitivity_specificity"]
