"""Pure-NumPy ranking metrics: AUROC and AUPRC (deterministic, tie-aware)."""

from __future__ import annotations

import numpy as np

from evaluation.metrics.classification import MetricInputError


def _validate_binary(y_true: np.ndarray, y_score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    yt = np.asarray(y_true)
    ys = np.asarray(y_score, dtype=np.float64)
    if yt.shape != ys.shape:
        raise MetricInputError("y_true and y_score must have the same shape")
    if yt.ndim != 1:
        raise MetricInputError("ranking metrics require 1-D inputs")
    unique = {int(v) for v in np.unique(yt)}
    if not unique <= {0, 1}:
        raise MetricInputError("AUROC/AUPRC require binary labels in {0, 1}")
    return yt.astype(np.int64), ys


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Ranks (1-based) with ties assigned their average rank — deterministic."""
    order = np.argsort(values, kind="mergesort")
    sorted_vals = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    n = len(values)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        ranks[order[i : j + 1]] = avg
        i = j + 1
    return ranks


def auroc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    """Area under the ROC curve via the rank (Mann-Whitney U) statistic.

    Returns ``None`` if the metric is undefined (only one class present).
    """
    yt, ys = _validate_binary(y_true, y_score)
    n_pos = int(np.sum(yt == 1))
    n_neg = int(np.sum(yt == 0))
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = _average_ranks(ys)
    sum_pos_ranks = float(np.sum(ranks[yt == 1]))
    auc = (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def auprc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    """Average precision (area under the precision-recall curve).

    Computed as the sum of ``(recall_k - recall_{k-1}) * precision_k`` over the
    score-sorted thresholds. Returns ``None`` if there are no positives.
    """
    yt, ys = _validate_binary(y_true, y_score)
    n_pos = int(np.sum(yt == 1))
    if n_pos == 0:
        return None

    order = np.argsort(-ys, kind="mergesort")  # descending score, stable
    yt_sorted = yt[order]
    tp = np.cumsum(yt_sorted == 1).astype(np.float64)
    fp = np.cumsum(yt_sorted == 0).astype(np.float64)
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / n_pos

    ap = 0.0
    prev_recall = 0.0
    for k in range(len(yt_sorted)):
        if recall[k] != prev_recall:
            ap += (recall[k] - prev_recall) * precision[k]
            prev_recall = recall[k]
    return float(ap)
