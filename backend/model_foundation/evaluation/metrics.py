"""Deterministic classification + calibration + uncertainty metrics (P4-G).

Pure NumPy; no randomness. All metrics are functions of (y_true, probs) and are
exactly reproducible.
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < n_classes and 0 <= p < n_classes:
            cm[int(t), int(p)] += 1
    return cm


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if y_true.size == 0:
        return 0.0
    return float(np.mean(y_true == y_pred))


def precision_recall_f1(cm: np.ndarray) -> tuple[float, float, float, dict]:
    """Macro-averaged precision / recall / F1 over classes present in ``y_true``."""
    n = cm.shape[0]
    per_class = {}
    precs, recs, f1s = [], [], []
    for c in range(n):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        support = cm[c, :].sum()
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class[str(c)] = {"precision": float(prec), "recall": float(rec),
                             "f1": float(f1), "support": int(support)}
        if support > 0:
            precs.append(prec)
            recs.append(rec)
            f1s.append(f1)
    macro_p = float(np.mean(precs)) if precs else 0.0
    macro_r = float(np.mean(recs)) if recs else 0.0
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0
    return macro_p, macro_r, macro_f1, per_class


def calibration_metrics(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> dict:
    """Expected Calibration Error (ECE) + multiclass Brier score."""
    if y_true.size == 0:
        return {"ece": 0.0, "brier": 0.0}
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == y_true).astype(float)
    ece = 0.0
    n = y_true.size
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        if mask.any():
            ece += (mask.sum() / n) * abs(correct[mask].mean() - conf[mask].mean())
    k = probs.shape[1]
    onehot = np.zeros((n, k))
    onehot[np.arange(n), np.clip(y_true, 0, k - 1)] = 1.0
    brier = float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))
    return {"ece": float(ece), "brier": brier}


def uncertainty_metrics(probs: np.ndarray) -> dict:
    """Mean predictive entropy + mean confidence."""
    if probs.size == 0:
        return {"mean_entropy": 0.0, "mean_confidence": 0.0}
    ent = -np.sum(probs * np.log(probs + _EPS), axis=1)
    norm = np.log(probs.shape[1]) if probs.shape[1] > 1 else 1.0
    return {"mean_entropy": float(np.mean(ent) / (norm + _EPS)),
            "mean_confidence": float(np.mean(probs.max(axis=1)))}
