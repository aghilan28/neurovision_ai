"""Shared deterministic helpers for the feature engines (internal).

Spectral estimation (Welch PSD), band-power integration, channel-region mapping,
and a ``FeatureVector`` builder. Pure NumPy/SciPy; no randomness, no learned state --
the same input always produces the same numbers.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import welch

from .models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector, FrequencyBand

DEFAULT_BANDS: tuple[FrequencyBand, ...] = (
    FrequencyBand.DELTA, FrequencyBand.THETA, FrequencyBand.ALPHA,
    FrequencyBand.BETA, FrequencyBand.GAMMA,
)

# Frontal/central/temporal/parietal/occipital region prefixes (10-20 montage style).
_REGION_PREFIXES = (
    ("frontal", ("fp", "af", "f")),
    ("central", ("c", "fc", "cp")),
    ("temporal", ("t", "ft", "tp")),
    ("parietal", ("p",)),
    ("occipital", ("o", "po")),
)
REGION_NAMES: tuple[str, ...] = ("frontal", "central", "temporal", "parietal", "occipital", "other")


def nperseg_for(n_samples: int, sfreq: float) -> int:
    """A deterministic Welch segment length that is stable on short recordings."""
    target = int(min(256, n_samples))
    return max(8, target)


def welch_psd(x: np.ndarray, sfreq: float, nperseg: int) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD of a 1-D signal (deterministic)."""
    nperseg = int(min(nperseg, x.size))
    freqs, psd = welch(x.astype(np.float64), fs=sfreq, nperseg=nperseg,
                       noverlap=nperseg // 2, detrend="constant", scaling="density")
    return freqs, psd


def band_power(freqs: np.ndarray, psd: np.ndarray, lo: float, hi: float) -> float:
    """Integrated PSD over [lo, hi) via the trapezoid rule."""
    mask = (freqs >= lo) & (freqs < hi)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(psd[mask], freqs[mask]))


def region_of_label(label: str) -> str:
    """Map a channel label to a coarse scalp region (deterministic, prefix-based)."""
    low = "".join(c for c in label.lower() if c.isalpha())
    best, best_len = "other", 0
    for region, prefixes in _REGION_PREFIXES:
        for p in prefixes:
            if low.startswith(p) and len(p) > best_len:
                best, best_len = region, len(p)
    return best


def make_vector(name: str, family: FeatureFamily, group: FeatureGroup, scope: FeatureScope,
                labels: tuple[str, ...], values, shape: tuple[int, ...],
                axes: tuple[str, ...] = (), units: str = "") -> FeatureVector:
    """Build a ``FeatureVector`` from a numeric array/sequence (flattened C-order)."""
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return FeatureVector(name=name, family=family, group=group, scope=scope, labels=tuple(labels),
                         values=tuple(float(v) for v in arr), shape=tuple(int(s) for s in shape),
                         axes=tuple(axes), units=units)
