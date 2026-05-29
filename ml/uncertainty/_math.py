"""Deterministic numerical helpers for the uncertainty layer.

Kept local to the uncertainty subsystem so it does not import the models module
(uncertainty operates on logits/probability arrays, not on model objects).
"""

from __future__ import annotations

import numpy as np


def softmax(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def negative_log_likelihood(probs: np.ndarray, labels: np.ndarray) -> float:
    y = np.asarray(labels, dtype=int)
    return float(-np.mean(np.log(probs[np.arange(probs.shape[0]), y] + 1e-12)))


def reliability_bins(probs: np.ndarray, labels: np.ndarray, n_bins: int) -> tuple[float, float, list]:
    """Top-1 confidence reliability bins -> (ECE, MCE, bins)."""
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == np.asarray(labels, dtype=int)).astype(np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = conf.size
    bins = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        mask = (conf >= lo) & (conf <= hi) if b == n_bins - 1 else (conf >= lo) & (conf < hi)
        count = int(mask.sum())
        if count == 0:
            bins.append({"lo": round(float(lo), 4), "hi": round(float(hi), 4),
                         "count": 0, "confidence": None, "accuracy": None, "gap": None})
            continue
        avg_conf = float(conf[mask].mean())
        avg_acc = float(correct[mask].mean())
        gap = abs(avg_conf - avg_acc)
        ece += (count / n) * gap
        mce = max(mce, gap)
        bins.append({"lo": round(float(lo), 4), "hi": round(float(hi), 4), "count": count,
                     "confidence": round(avg_conf, 6), "accuracy": round(avg_acc, 6),
                     "gap": round(gap, 6)})
    return float(ece), float(mce), bins


def brier(probs: np.ndarray, labels: np.ndarray) -> float:
    n, k = probs.shape
    onehot = np.zeros((n, k), dtype=np.float64)
    onehot[np.arange(n), np.asarray(labels, dtype=int)] = 1.0
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """The finite-sample-corrected (1-alpha) quantile used by split conformal.

    Uses the standard ceil((n+1)(1-alpha))/n level, which yields the marginal
    coverage guarantee P(y in set) >= 1 - alpha under exchangeability.
    """
    n = scores.size
    if n == 0:
        return 1.0
    level = np.ceil((n + 1) * (1.0 - alpha)) / n
    level = min(level, 1.0)
    return float(np.quantile(scores, level, method="higher"))
