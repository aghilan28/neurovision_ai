"""Deterministic NumPy neural-network primitives for the baseline models.

These are pure functions / small helpers used by the feature extractors. They are
deterministic (no randomness here; randomness only enters via seeded weight
initialization in the model classes) and vectorized for speed on CPU.

Conventions
-----------
Signals are ``(N, C, T)``: batch, channels, time. Convolutions act along time.
"""

from __future__ import annotations

import numpy as np


def he_uniform(rng: np.random.Generator, shape: tuple[int, ...], fan_in: int) -> np.ndarray:
    """He-uniform initialization (deterministic given ``rng``)."""
    limit = np.sqrt(6.0 / max(1, fan_in))
    return rng.uniform(-limit, limit, size=shape).astype(np.float64)


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def elu(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    return np.where(x > 0, x, alpha * (np.exp(np.clip(x, -30, 0)) - 1.0))


def _im2col_time(x: np.ndarray, k: int, stride: int, dilation: int, pad_left: int, pad_right: int) -> np.ndarray:
    """Extract sliding (dilated) time patches.

    ``x`` : (N, Cin, T) -> patches (N, Cin, T_out, k).
    """
    n, cin, t = x.shape
    if pad_left or pad_right:
        x = np.pad(x, ((0, 0), (0, 0), (pad_left, pad_right)))
    t_eff = x.shape[2]
    span = (k - 1) * dilation + 1
    t_out = (t_eff - span) // stride + 1
    if t_out <= 0:
        raise ValueError("convolution span exceeds input length")
    base = np.arange(t_out) * stride
    off = np.arange(k) * dilation
    idx = base[:, None] + off[None, :]          # (t_out, k)
    patches = x[:, :, idx]                        # (N, Cin, t_out, k)
    return patches


def conv1d(
    x: np.ndarray,
    weight: np.ndarray,
    bias: np.ndarray | None = None,
    stride: int = 1,
    dilation: int = 1,
    padding: int = 0,
    groups: int = 1,
    causal: bool = False,
) -> np.ndarray:
    """1-D convolution along time.

    ``x``      : (N, Cin, T)
    ``weight`` : (Cout, Cin // groups, k)
    returns    : (N, Cout, T_out)

    ``causal`` left-pads by ``(k-1)*dilation`` so output length equals input length
    and no future sample influences the present (used by the TCN).
    """
    n, cin, t = x.shape
    cout, cin_g, k = weight.shape
    if groups == 1 and cin_g != cin:
        raise ValueError("weight in-channels must match x channels when groups==1")
    if cin % groups != 0 or cout % groups != 0:
        raise ValueError("channels must be divisible by groups")

    if causal:
        pad_left, pad_right = (k - 1) * dilation, 0
    else:
        pad_left = pad_right = padding

    patches = _im2col_time(x, k, stride, dilation, pad_left, pad_right)  # (N, Cin, t_out, k)

    if groups == 1:
        out = np.einsum("nctk,ock->not", patches, weight, optimize=True)
    else:
        cin_per = cin // groups
        cout_per = cout // groups
        t_out = patches.shape[2]
        out = np.empty((n, cout, t_out), dtype=np.float64)
        for g in range(groups):
            p = patches[:, g * cin_per : (g + 1) * cin_per]           # (N, cin_per, t_out, k)
            w = weight[g * cout_per : (g + 1) * cout_per]             # (cout_per, cin_per, k)
            out[:, g * cout_per : (g + 1) * cout_per] = np.einsum(
                "nctk,ock->not", p, w, optimize=True
            )
    if bias is not None:
        out = out + bias[None, :, None]
    return out


def avg_pool_time(x: np.ndarray, size: int) -> np.ndarray:
    """Non-overlapping average pooling along time. ``x``: (N, C, T)."""
    if size <= 1:
        return x
    n, c, t = x.shape
    t_trim = (t // size) * size
    if t_trim == 0:
        return x.mean(axis=2, keepdims=True)
    xt = x[:, :, :t_trim].reshape(n, c, t_trim // size, size)
    return xt.mean(axis=3)


def global_stats_pool(x: np.ndarray) -> np.ndarray:
    """Global average + std pooling along time -> feature vector.

    ``x``: (N, C, T) -> (N, 2C). Captures both the mean activation and its temporal
    variability, which is informative for rhythmic vs. periodic EEG morphology.
    """
    mean = x.mean(axis=2)
    std = x.std(axis=2)
    return np.concatenate([mean, std], axis=1)
