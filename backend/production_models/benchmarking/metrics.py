"""Deterministic ranking metrics for benchmarking (DRP2-E).

Pure NumPy ROC-AUC and PR-AUC (one-vs-rest, macro-averaged over the classes present),
complementing the model-foundation classification + calibration metrics (reused, not
duplicated). All metrics are functions of (y_true, probs) and are exactly reproducible.
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


def _binary_roc_auc(y_true_bin: np.ndarray, scores: np.ndarray) -> float:
    """ROC-AUC via the rank-sum (Mann-Whitney U) identity, with tie handling."""
    n_pos = float(np.sum(y_true_bin == 1))
    n_neg = float(np.sum(y_true_bin == 0))
    if n_pos == 0 or n_neg == 0:
        return 0.0
    order = np.argsort(scores, kind="mergesort")
    ranked = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    i = 0
    n = len(scores)
    while i < n:
        j = i
        while j + 1 < n and ranked[j + 1] == ranked[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0          # 1-based average rank for ties
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    sum_pos_ranks = float(np.sum(ranks[y_true_bin == 1]))
    auc = (sum_pos_ranks - n_pos * (n_pos + 1.0) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _binary_pr_auc(y_true_bin: np.ndarray, scores: np.ndarray) -> float:
    """Average precision (area under the precision-recall curve)."""
    n_pos = float(np.sum(y_true_bin == 1))
    if n_pos == 0:
        return 0.0
    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y_true_bin[order]
    tp = np.cumsum(y_sorted == 1)
    fp = np.cumsum(y_sorted == 0)
    precision = tp / np.maximum(tp + fp, _EPS)
    recall = tp / n_pos
    # sum of precision at each positive (step) — the standard average-precision estimator
    ap = 0.0
    prev_recall = 0.0
    for k in range(len(y_sorted)):
        if y_sorted[k] == 1:
            ap += precision[k] * (recall[k] - prev_recall)
            prev_recall = recall[k]
    return float(ap)


def roc_auc_macro(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Macro one-vs-rest ROC-AUC over the classes present in ``y_true``."""
    y_true = np.asarray(y_true, dtype=int)
    if y_true.size == 0 or probs.size == 0:
        return 0.0
    aucs = []
    for c in range(probs.shape[1]):
        bin_true = (y_true == c).astype(int)
        if 0 < bin_true.sum() < y_true.size:
            aucs.append(_binary_roc_auc(bin_true, probs[:, c]))
    return float(np.mean(aucs)) if aucs else 0.0


def pr_auc_macro(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Macro one-vs-rest PR-AUC (average precision) over present classes."""
    y_true = np.asarray(y_true, dtype=int)
    if y_true.size == 0 or probs.size == 0:
        return 0.0
    aps = []
    for c in range(probs.shape[1]):
        bin_true = (y_true == c).astype(int)
        if bin_true.sum() > 0:
            aps.append(_binary_pr_auc(bin_true, probs[:, c]))
    return float(np.mean(aps)) if aps else 0.0
