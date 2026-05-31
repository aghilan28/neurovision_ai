"""Production model evaluation analyses (DRP2-F).

Deterministic, structured evaluation analyses over a fitted model on the dataset's test
split: confusion matrix, calibration analysis, error analysis, class-distribution
analysis, stability analysis (predictions under a fixed deterministic perturbation set),
and reliability analysis (binned confidence vs accuracy). Plus a cross-model comparison.
Structured outputs only — no images, no UI. References the base ``evaluation_id`` from the
reused model-foundation evaluator.
"""

from __future__ import annotations

import numpy as np

from backend.model_foundation import metrics as M  # reuse confusion + calibration metrics

from ..identity import mint_identity
from ..models.domain import ModelEvaluationRecord
from ..version import DETERMINISTIC_EPOCH

# A fixed, deterministic perturbation set for stability analysis (no randomness).
_STABILITY_SCALES = (1e-3, 5e-3, 1e-2)


def _resolve_eval_idx(bundle):
    for name in ("test", "val", "train"):
        idx = bundle.split_indices(name)
        if idx.size:
            return name, idx
    return "test", np.array([], dtype=int)


def _error_analysis(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> dict:
    n = int(y_true.size)
    errors = int(np.sum(y_true != y_pred)) if n else 0
    per_class = {}
    for c in range(n_classes):
        support = int(np.sum(y_true == c))
        miss = int(np.sum((y_true == c) & (y_pred != c)))
        per_class[str(c)] = {"support": support, "errors": miss,
                             "error_rate": float(miss / support) if support else 0.0}
    # most-confused ordered (true,pred) pair
    confused = {}
    for t, p in zip(y_true.tolist(), y_pred.tolist()):
        if t != p:
            confused[f"{t}->{p}"] = confused.get(f"{t}->{p}", 0) + 1
    top = sorted(confused.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return {"n_samples": n, "n_errors": errors,
            "overall_error_rate": float(errors / n) if n else 0.0,
            "per_class": per_class, "top_confusions": dict(top)}


def _class_distribution_analysis(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> dict:
    n = int(y_true.size)
    true_dist = {str(c): int(np.sum(y_true == c)) for c in range(n_classes)}
    pred_dist = {str(c): int(np.sum(y_pred == c)) for c in range(n_classes)}
    # max absolute proportion gap between predicted and true class shares
    gap = 0.0
    if n:
        for c in range(n_classes):
            gap = max(gap, abs(true_dist[str(c)] - pred_dist[str(c)]) / n)
    return {"n_samples": n, "true_distribution": true_dist, "predicted_distribution": pred_dist,
            "max_distribution_gap": float(gap)}


def _stability_analysis(model, X: np.ndarray, base_pred: np.ndarray) -> dict:
    """Fraction of predictions unchanged under a fixed deterministic perturbation set."""
    if X.shape[0] == 0:
        return {"n_samples": 0, "stability_score": 1.0, "per_scale": {}}
    scale = np.maximum(np.std(X, axis=0, keepdims=True), 1e-9)
    per_scale = {}
    agreements = []
    for eps in _STABILITY_SCALES:
        # deterministic sign pattern (alternating) — no randomness
        sign = np.where((np.arange(X.shape[1]) % 2) == 0, 1.0, -1.0)
        Xp = X + eps * scale * sign
        pred = model.predict(Xp)
        agree = float(np.mean(pred == base_pred))
        per_scale[f"{eps:g}"] = agree
        agreements.append(agree)
    return {"n_samples": int(X.shape[0]), "stability_score": float(np.mean(agreements)),
            "per_scale": per_scale}


def _reliability_analysis(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> dict:
    if y_true.size == 0:
        return {"n_bins": n_bins, "bins": [], "mean_confidence": 0.0, "accuracy": 0.0}
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == y_true).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        count = int(mask.sum())
        bins.append({"lo": float(lo), "hi": float(hi), "count": count,
                     "confidence": float(conf[mask].mean()) if count else 0.0,
                     "accuracy": float(correct[mask].mean()) if count else 0.0})
    return {"n_bins": n_bins, "bins": bins, "mean_confidence": float(conf.mean()),
            "accuracy": float(correct.mean())}


def build_model_evaluation(model, bundle, *, model_id: str, evaluation_id: str, n_classes: int,
                           created_at: str = DETERMINISTIC_EPOCH) -> ModelEvaluationRecord:
    """Compute the full structured evaluation analyses for a fitted model."""
    split, idx = _resolve_eval_idx(bundle)
    X, y = bundle.X[idx], bundle.y[idx]
    probs = model.predict_proba(X) if idx.size else np.zeros((0, n_classes))
    y_pred = probs.argmax(axis=1) if idx.size else np.array([], dtype=int)

    cm = M.confusion_matrix(y, y_pred, n_classes)
    calibration = M.calibration_metrics(y, probs)
    confusion = tuple(tuple(int(v) for v in row) for row in cm.tolist())

    from ml.provenance import hash_obj
    eval_key = hash_obj({"model_id": model_id, "evaluation_id": evaluation_id,
                         "confusion": [list(r) for r in confusion]})
    model_evaluation_id = mint_identity("model_evaluation",
                                        {"model_id": model_id, "eval_key": eval_key}).id

    return ModelEvaluationRecord(
        model_evaluation_id=model_evaluation_id, model_id=model_id, evaluation_id=evaluation_id,
        dataset_id=bundle.record.dataset_id, split=split, confusion_matrix=confusion,
        calibration_analysis={"ece": calibration["ece"], "brier": calibration["brier"]},
        error_analysis=_error_analysis(y, y_pred, n_classes),
        class_distribution_analysis=_class_distribution_analysis(y, y_pred, n_classes),
        stability_analysis=_stability_analysis(model, X, y_pred),
        reliability_analysis=_reliability_analysis(y, probs), created_at=created_at)


# =============================================================================
# Cross-model comparison (DRP2-F)
# =============================================================================
_COMPARISON_METRICS = ("accuracy", "f1_macro", "roc_auc_macro", "pr_auc_macro")


def compare_models(benchmarks: list) -> dict:
    """Compare >=2 benchmarked models -> ranking, best-per-metric, recommended model.

    Deterministic: ties are broken by ``model_id`` so the recommendation is reproducible.
    ``recommended_model`` maximizes f1 then accuracy then roc_auc (then model_id)."""
    rows = []
    for b in benchmarks:
        m = b.deterministic_metrics
        rows.append({"model_id": b.model_id, "architecture": b.architecture.value,
                     "metrics": {k: float(m.get(k, 0.0)) for k in _COMPARISON_METRICS}})
    best_per_metric = {}
    for metric in _COMPARISON_METRICS:
        if rows:
            best = max(rows, key=lambda r: (r["metrics"][metric], r["model_id"]))
            best_per_metric[metric] = {"model_id": best["model_id"],
                                       "architecture": best["architecture"],
                                       "value": best["metrics"][metric]}
    ranking = sorted(
        rows,
        key=lambda r: (-r["metrics"]["f1_macro"], -r["metrics"]["accuracy"],
                       -r["metrics"]["roc_auc_macro"], r["model_id"]))
    recommended = ranking[0]["model_id"] if ranking else None
    return {"n_models": len(rows), "metrics": list(_COMPARISON_METRICS),
            "models": rows, "ranking": [r["model_id"] for r in ranking],
            "best_per_metric": best_per_metric, "recommended_model": recommended}
