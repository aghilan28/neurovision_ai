"""Deterministic, versioned EEG preprocessing transforms (DSP layer).

This module turns raw EEG windows into clean, normalized, model-ready signal in a
way that is **deterministic and versioned** (AP-3 / NR-9): for a fixed
``PreprocessingConfig`` and ``PREPROCESSING_VERSION``, the same input always
produces the same output, byte for byte.

Contract
--------
Input  : float array of shape ``(n_windows, n_channels, n_samples)`` (a batch) or
         ``(n_channels, n_samples)`` (a single window).
Output : float32 array of the same shape, conditioned and normalized.

The transforms are pure functions of their inputs and the config. There is no
randomness, no wall-clock dependence, and no global mutable state.

Boundary: imports nobody internal (NR-8); depends only on pinned NumPy.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from .version import PREPROCESSING_VERSION
from ._provenance import hash_obj


@dataclass(frozen=True)
class PreprocessingConfig:
    """Pinned, hashable preprocessing parameters.

    Every field affects the output and therefore the provenance signature. The
    config is frozen so it cannot mutate after creation (reproducibility).
    """

    highpass_window: int = 33  # moving-average window (samples) removed as baseline drift
    smooth_window: int = 3     # moving-average smoothing window (samples)
    clip_sigma: float = 8.0    # winsorization threshold in robust-sigma units
    eps: float = 1e-6          # numerical floor for normalization

    def __post_init__(self) -> None:
        if self.highpass_window < 1 or self.highpass_window % 2 == 0:
            raise ValueError("highpass_window must be a positive odd integer")
        if self.smooth_window < 1 or self.smooth_window % 2 == 0:
            raise ValueError("smooth_window must be a positive odd integer")
        if self.clip_sigma <= 0:
            raise ValueError("clip_sigma must be positive")
        if self.eps <= 0:
            raise ValueError("eps must be positive")

    def as_dict(self) -> dict:
        return asdict(self)


def preprocessing_signature(config: PreprocessingConfig) -> str:
    """Return a content hash binding the preprocessing version to the config.

    This signature is recorded as provenance with every downstream artifact so a
    result can always be traced to the exact transform that produced it (AP-5).
    """
    return hash_obj({"version": PREPROCESSING_VERSION, "config": config.as_dict()})


def _moving_average(x: np.ndarray, window: int) -> np.ndarray:
    """Deterministic centered moving average along the last axis.

    Edge samples use a shrinking symmetric window (reflect-free, deterministic).
    """
    if window == 1:
        return x.astype(np.float64, copy=True)
    pad = window // 2
    # Cumulative-sum based moving average with explicit edge normalization.
    cs = np.cumsum(np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad + 1, pad)], mode="edge"), axis=-1)
    out = (cs[..., window:] - cs[..., :-window]) / float(window)
    return out[..., : x.shape[-1]]


def _detrend_last_axis(x: np.ndarray) -> np.ndarray:
    """Remove a per-trace linear trend along the last axis (deterministic)."""
    n = x.shape[-1]
    t = np.linspace(-1.0, 1.0, n, dtype=np.float64)
    # Least-squares slope/intercept in closed form (t has zero mean).
    t_mean = t.mean()
    tc = t - t_mean
    denom = np.sum(tc * tc)
    x_mean = x.mean(axis=-1, keepdims=True)
    slope = np.sum((x - x_mean) * tc, axis=-1, keepdims=True) / denom
    trend = slope * tc + x_mean
    return x - trend


def _robust_zscore(x: np.ndarray, eps: float) -> np.ndarray:
    """Per-trace robust z-score using median and MAD along the last axis."""
    med = np.median(x, axis=-1, keepdims=True)
    mad = np.median(np.abs(x - med), axis=-1, keepdims=True)
    scale = 1.4826 * mad + eps  # 1.4826 makes MAD a consistent sigma estimate for normals
    return (x - med) / scale


def transform(x: np.ndarray, config: PreprocessingConfig | None = None) -> np.ndarray:
    """Apply the deterministic preprocessing pipeline.

    Accepts a single window ``(C, T)`` or a batch ``(N, C, T)`` and returns the
    conditioned signal as float32 with the same shape.
    """
    if config is None:
        config = PreprocessingConfig()

    arr = np.asarray(x, dtype=np.float64)
    single = arr.ndim == 2
    if single:
        arr = arr[None, ...]
    if arr.ndim != 3:
        raise ValueError(f"expected (C, T) or (N, C, T) input, got shape {x.shape!r}")

    # 1) linear detrend (remove slow baseline drift deterministically)
    arr = _detrend_last_axis(arr)
    # 2) high-pass: subtract a long moving average
    arr = arr - _moving_average(arr, config.highpass_window)
    # 3) low-pass: short moving-average smoothing to suppress high-frequency jitter
    arr = _moving_average(arr, config.smooth_window)
    # 4) robust per-channel normalization
    arr = _robust_zscore(arr, config.eps)
    # 5) winsorize extreme values for stability
    arr = np.clip(arr, -config.clip_sigma, config.clip_sigma)

    out = arr.astype(np.float32)
    return out[0] if single else out
