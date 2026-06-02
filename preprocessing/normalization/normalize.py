"""Normalization implementations (deterministic, per-channel)."""

from __future__ import annotations

import numpy as np

from preprocessing.schemas.enums import NormalizationMethod

#: Version of the normalization operation (recorded on lineage).
NORMALIZATION_OP_VERSION = "1.0.0"


def _zscore(values: np.ndarray, axis: int, epsilon: float) -> np.ndarray:
    mean = np.mean(values, axis=axis, keepdims=True)
    std = np.std(values, axis=axis, keepdims=True)
    return (values - mean) / np.maximum(std, epsilon)


def _robust(values: np.ndarray, axis: int, epsilon: float) -> np.ndarray:
    median = np.median(values, axis=axis, keepdims=True)
    q75 = np.percentile(values, 75, axis=axis, keepdims=True)
    q25 = np.percentile(values, 25, axis=axis, keepdims=True)
    iqr = q75 - q25
    return (values - median) / np.maximum(iqr, epsilon)


def normalize_per_channel(
    signals: np.ndarray,
    method: NormalizationMethod,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Normalize a 2-D ``(channels, samples)`` array, statistics per channel over time."""
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    if method is NormalizationMethod.NONE or arr.shape[-1] == 0:
        return arr
    if method is NormalizationMethod.ZSCORE:
        out = _zscore(arr, axis=-1, epsilon=epsilon)
    elif method is NormalizationMethod.ROBUST:
        out = _robust(arr, axis=-1, epsilon=epsilon)
    else:  # pragma: no cover - exhaustive enum
        raise ValueError(f"unsupported normalization method {method!r}")
    return np.ascontiguousarray(out, dtype=np.float64)


def normalize_per_window(
    windows: np.ndarray,
    method: NormalizationMethod,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Normalize a 3-D ``(windows, channels, samples)`` array per window per channel."""
    arr = np.ascontiguousarray(np.asarray(windows, dtype=np.float64))
    if method is NormalizationMethod.NONE or arr.size == 0:
        return arr
    if method is NormalizationMethod.ZSCORE:
        out = _zscore(arr, axis=-1, epsilon=epsilon)
    elif method is NormalizationMethod.ROBUST:
        out = _robust(arr, axis=-1, epsilon=epsilon)
    else:  # pragma: no cover - exhaustive enum
        raise ValueError(f"unsupported normalization method {method!r}")
    return np.ascontiguousarray(out, dtype=np.float64)
