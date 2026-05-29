"""Patient-disjoint classification metrics (deterministic).

Computes overall and per-class detection metrics for the SZ + IIC classes,
including sensitivity/specificity (the clinically meaningful framing) and macro
averages. All metrics are pure functions of the inputs, so they are reproducible.
"""

from __future__ import annotations

import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> np.ndarray:
    cm = np.zeros((k, k), dtype=np.int64)
    for t, p in zip(y_true.astype(int), y_pred.astype(int)):
        cm[t, p] += 1
    return cm


def _auroc_ovr(scores: np.ndarray, positive: np.ndarray) -> float | None:
    """One-vs-rest AUROC via the Mann-Whitney U statistic (rank method)."""
    pos = scores[positive]
    neg = scores[~positive]
    if pos.size == 0 or neg.size == 0:
        return None
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, scores.size + 1)
    # average ranks for ties
    _assign_tie_ranks(scores, ranks)
    sum_pos = ranks[positive].sum()
    n_pos = pos.size
    n_neg = neg.size
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _assign_tie_ranks(scores: np.ndarray, ranks: np.ndarray) -> None:
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    i = 0
    n = scores.size
    while i < n:
        j = i
        while j + 1 < n and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            avg = (i + 1 + j + 1) / 2.0
            ranks[order[i : j + 1]] = avg
        i = j + 1


def compute_metrics(
    probabilities: np.ndarray,
    labels: np.ndarray,
    class_names: tuple[str, ...],
) -> tuple[dict, dict]:
    """Return ``(overall_metrics, per_class_metrics)``."""
    k = len(class_names)
    y_true = np.asarray(labels, dtype=int)
    y_pred = probabilities.argmax(axis=1)
    cm = confusion_matrix(y_true, y_pred, k)
    total = int(cm.sum())

    per_class: dict[str, dict] = {}
    sens_list, spec_list, prec_list, f1_list, auroc_list = [], [], [], [], []
    for c in range(k):
        tp = int(cm[c, c])
        fn = int(cm[c, :].sum() - tp)
        fp = int(cm[:, c].sum() - tp)
        tn = int(total - tp - fn - fp)
        sens = tp / (tp + fn) if (tp + fn) else 0.0
        spec = tn / (tn + fp) if (tn + fp) else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        f1 = (2 * prec * sens / (prec + sens)) if (prec + sens) else 0.0
        auroc = _auroc_ovr(probabilities[:, c], y_true == c)
        per_class[class_names[c]] = {
            "support": int(tp + fn),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "sensitivity": round(sens, 6),
            "specificity": round(spec, 6),
            "precision": round(prec, 6),
            "f1": round(f1, 6),
            "auroc": None if auroc is None else round(auroc, 6),
        }
        sens_list.append(sens)
        spec_list.append(spec)
        prec_list.append(prec)
        f1_list.append(f1)
        if auroc is not None:
            auroc_list.append(auroc)

    accuracy = float(np.trace(cm) / total) if total else 0.0
    overall = {
        "accuracy": round(accuracy, 6),
        "balanced_accuracy": round(float(np.mean(sens_list)), 6),
        "macro_sensitivity": round(float(np.mean(sens_list)), 6),
        "macro_specificity": round(float(np.mean(spec_list)), 6),
        "macro_precision": round(float(np.mean(prec_list)), 6),
        "macro_f1": round(float(np.mean(f1_list)), 6),
        "macro_auroc": round(float(np.mean(auroc_list)), 6) if auroc_list else None,
        "n": total,
        "confusion_matrix": cm.tolist(),
        "class_names": list(class_names),
    }
    return overall, per_class
