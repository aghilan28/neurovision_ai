"""Calibration & coverage *measurement* (evaluation's responsibility, AP-4).

The evaluation layer independently measures calibration quality (ECE, MCE, Brier)
and conformal coverage. This is distinct from the uncertainty layer's *production*
of calibrated outputs (ml/uncertainty): evaluation verifies; ml/uncertainty fits.
Keeping both is deliberate — the verifier never trusts the producer's own numbers.
"""

from __future__ import annotations

import numpy as np


def expected_calibration_error(
    probabilities: np.ndarray, labels: np.ndarray, n_bins: int = 10
) -> tuple[float, float, list]:
    """Return ``(ECE, MCE, bins)`` for top-1 confidence calibration."""
    conf = probabilities.max(axis=1)
    pred = probabilities.argmax(axis=1)
    correct = (pred == np.asarray(labels, dtype=int)).astype(np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = conf.size
    bins = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        if b == n_bins - 1:
            mask = (conf >= lo) & (conf <= hi)
        else:
            mask = (conf >= lo) & (conf < hi)
        count = int(mask.sum())
        if count == 0:
            bins.append({"lo": round(float(lo), 4), "hi": round(float(hi), 4),
                         "count": 0, "confidence": None, "accuracy": None})
            continue
        avg_conf = float(conf[mask].mean())
        avg_acc = float(correct[mask].mean())
        gap = abs(avg_conf - avg_acc)
        ece += (count / n) * gap
        mce = max(mce, gap)
        bins.append({
            "lo": round(float(lo), 4), "hi": round(float(hi), 4),
            "count": count,
            "confidence": round(avg_conf, 6),
            "accuracy": round(avg_acc, 6),
        })
    return float(ece), float(mce), bins


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    """Multiclass Brier score (mean squared error vs. one-hot truth)."""
    n, k = probabilities.shape
    onehot = np.zeros((n, k), dtype=np.float64)
    onehot[np.arange(n), np.asarray(labels, dtype=int)] = 1.0
    return float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1)))


def empirical_coverage(prediction_sets: np.ndarray, labels: np.ndarray) -> float:
    """Fraction of windows whose true label is inside the prediction set."""
    y = np.asarray(labels, dtype=int)
    hit = prediction_sets[np.arange(prediction_sets.shape[0]), y]
    return float(np.mean(hit))


def average_set_size(prediction_sets: np.ndarray) -> float:
    return float(prediction_sets.sum(axis=1).mean())
