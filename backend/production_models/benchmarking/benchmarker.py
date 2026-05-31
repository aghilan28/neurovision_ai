"""Production benchmarking program (DRP2-E).

Benchmarks a fitted production model on the dataset's test split and produces a
reproducible :class:`ModelBenchmarkRecord`. The benchmark tracks **deterministic** metrics
(accuracy / precision / recall / F1 / ROC-AUC / PR-AUC / calibration ECE + Brier) — which
enter the benchmark id + signature — and **informational** performance measures
(inference time, per-sample latency, peak memory, training time) which are measured live
and excluded from every signature so verdicts reproduce bit-for-bit (NR-9/NR-10).
"""

from __future__ import annotations

import time
import tracemalloc

import numpy as np

from backend.model_foundation import metrics as M  # reuse classification + calibration metrics

from ..identity import mint_identity
from ..models.domain import (
    BenchmarkVersion, ModelBenchmarkRecord, ProductionArchitecture,
)
from ..version import DETERMINISTIC_EPOCH
from . import metrics as RM


def benchmark_model(model, bundle, *, model_id: str, architecture: ProductionArchitecture,
                    n_classes: int, training_time_ms: float = 0.0, split: str = "test",
                    created_at: str = DETERMINISTIC_EPOCH) -> ModelBenchmarkRecord:
    """Benchmark ``model`` on the dataset's ``split``; deterministic ``ModelBenchmarkRecord``."""
    idx = bundle.split_indices(split if split in ("train", "val", "test") else "test")
    if idx.size == 0:  # fall back to any non-empty split so a benchmark always exists
        for alt in ("test", "val", "train"):
            idx = bundle.split_indices(alt)
            if idx.size:
                split = alt
                break
    X, y = bundle.X[idx], bundle.y[idx]

    # --- informational performance (NEVER hashed) -----------------------------
    tracemalloc.start()
    t0 = time.perf_counter()
    probs = model.predict_proba(X) if idx.size else np.zeros((0, n_classes))
    inference_time_ms = (time.perf_counter() - t0) * 1000.0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    n = max(1, int(idx.size))
    performance = {
        "training_time_ms": float(training_time_ms),
        "inference_time_ms": float(inference_time_ms),
        "latency_ms_per_sample": float(inference_time_ms / n),
        "peak_memory_kb": float(peak) / 1024.0,
    }

    # --- deterministic metrics (hashed) ---------------------------------------
    y_pred = probs.argmax(axis=1) if idx.size else np.array([], dtype=int)
    cm = M.confusion_matrix(y, y_pred, n_classes)
    acc = M.accuracy(y, y_pred)
    macro_p, macro_r, macro_f1, _per_class = M.precision_recall_f1(cm)
    calibration = M.calibration_metrics(y, probs)
    deterministic_metrics = {
        "accuracy": acc, "precision_macro": macro_p, "recall_macro": macro_r,
        "f1_macro": macro_f1, "roc_auc_macro": RM.roc_auc_macro(y, probs),
        "pr_auc_macro": RM.pr_auc_macro(y, probs), "ece": calibration["ece"],
        "brier": calibration["brier"],
    }

    benchmark_key = {"model_id": model_id, "architecture": architecture.value,
                     "dataset_id": bundle.record.dataset_id, "split": split,
                     "deterministic_metrics": {k: round(float(v), 9)
                                               for k, v in sorted(deterministic_metrics.items())},
                     "n_samples": int(idx.size), "n_classes": int(n_classes)}
    from ml.provenance import hash_obj
    metrics_sig = hash_obj(benchmark_key)
    benchmark_id = mint_identity("benchmark", {"model_id": model_id, "benchmark_key": metrics_sig}).id
    version = BenchmarkVersion(version=BenchmarkVersion.compute(metrics_sig, None), previous=None,
                               reason="benchmarked", created_at=created_at)

    return ModelBenchmarkRecord(
        benchmark_id=benchmark_id, model_id=model_id, architecture=architecture,
        dataset_id=bundle.record.dataset_id, split=split,
        deterministic_metrics=deterministic_metrics, performance=performance,
        n_samples=int(idx.size), n_classes=int(n_classes), version=version, created_at=created_at)
