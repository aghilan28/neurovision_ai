"""Pure-NumPy classification metrics (deterministic, no third-party ML library)."""

from __future__ import annotations

from typing import Any

import numpy as np


class MetricInputError(ValueError):
    """Raised when metric inputs are malformed (shape/label mismatch)."""


def _as_int_labels(y: np.ndarray) -> np.ndarray:
    arr = np.asarray(y)
    if arr.ndim != 1:
        raise MetricInputError("labels must be 1-D")
    return arr.astype(np.int64)


def resolve_labels(
    y_true: np.ndarray, y_pred: np.ndarray, labels: tuple[int, ...] | None
) -> np.ndarray:
    """Return the sorted label set (explicit, or the union observed in the data)."""
    if labels is not None:
        return np.asarray(sorted({int(x) for x in labels}), dtype=np.int64)
    union = np.union1d(np.unique(y_true), np.unique(y_pred))
    return union.astype(np.int64)


def confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray, *, labels: tuple[int, ...] | None = None
) -> np.ndarray:
    """Confusion matrix ``C`` where ``C[i, j]`` counts true label i predicted as j."""
    yt = _as_int_labels(y_true)
    yp = _as_int_labels(y_pred)
    if yt.shape != yp.shape:
        raise MetricInputError("y_true and y_pred must have the same shape")
    label_arr = resolve_labels(yt, yp, labels)
    index = {int(lbl): i for i, lbl in enumerate(label_arr)}
    k = len(label_arr)
    cm = np.zeros((k, k), dtype=np.int64)
    for t, p in zip(yt, yp, strict=True):
        ti, pi = index.get(int(t)), index.get(int(p))
        if ti is None or pi is None:
            raise MetricInputError(f"observed label not in provided labels: {int(t)}/{int(p)}")
        cm[ti, pi] += 1
    return cm


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Overall accuracy (fraction correct)."""
    yt = _as_int_labels(y_true)
    yp = _as_int_labels(y_pred)
    if yt.shape != yp.shape:
        raise MetricInputError("y_true and y_pred must have the same shape")
    if yt.size == 0:
        return 0.0
    return float(np.mean(yt == yp))


def precision_recall(
    y_true: np.ndarray, y_pred: np.ndarray, *, labels: tuple[int, ...] | None = None
) -> dict[str, Any]:
    """Per-class precision/recall/F1 plus macro averages.

    Returns ``{"per_class": {label: {precision, recall, f1, support}}, "macro": {...}}``.
    """
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    label_arr = resolve_labels(_as_int_labels(y_true), _as_int_labels(y_pred), labels)
    tp = np.diag(cm).astype(np.float64)
    pred_pos = cm.sum(axis=0).astype(np.float64)
    actual_pos = cm.sum(axis=1).astype(np.float64)

    per_class: dict[str, dict[str, float]] = {}
    precisions, recalls, f1s = [], [], []
    for i, lbl in enumerate(label_arr):
        prec = float(tp[i] / pred_pos[i]) if pred_pos[i] > 0 else 0.0
        rec = float(tp[i] / actual_pos[i]) if actual_pos[i] > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class[str(int(lbl))] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(actual_pos[i]),
        }
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    macro = {
        "precision": float(np.mean(precisions)) if precisions else 0.0,
        "recall": float(np.mean(recalls)) if recalls else 0.0,
        "f1": float(np.mean(f1s)) if f1s else 0.0,
    }
    return {"per_class": per_class, "macro": macro}


def f1_score(
    y_true: np.ndarray, y_pred: np.ndarray, *, labels: tuple[int, ...] | None = None
) -> float:
    """Macro-averaged F1 score."""
    return precision_recall(y_true, y_pred, labels=labels)["macro"]["f1"]


def balanced_accuracy(
    y_true: np.ndarray, y_pred: np.ndarray, *, labels: tuple[int, ...] | None = None
) -> float:
    """Balanced accuracy: the mean per-class recall (robust to class imbalance)."""
    pr = precision_recall(y_true, y_pred, labels=labels)
    recalls = [v["recall"] for v in pr["per_class"].values()]
    return float(np.mean(recalls)) if recalls else 0.0


def sensitivity_specificity(
    y_true: np.ndarray, y_pred: np.ndarray, *, positive_label: int = 1
) -> dict[str, float]:
    """Binary sensitivity (recall of positive) and specificity (recall of negative)."""
    yt = _as_int_labels(y_true)
    yp = _as_int_labels(y_pred)
    if yt.shape != yp.shape:
        raise MetricInputError("y_true and y_pred must have the same shape")
    pos = yt == positive_label
    neg = ~pos
    tp = int(np.sum(pos & (yp == positive_label)))
    fn = int(np.sum(pos & (yp != positive_label)))
    tn = int(np.sum(neg & (yp != positive_label)))
    fp = int(np.sum(neg & (yp == positive_label)))
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return {"sensitivity": float(sensitivity), "specificity": float(specificity)}
