"""Baseline-drift handling via detrending.

Slow baseline drift (electrode/sweat/movement) is primarily addressed by the
bandpass high-pass edge. For explicit removal, ``apply_detrend`` performs a
deterministic ``linear`` (or ``constant``) detrend per channel.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal


def apply_detrend(signals: np.ndarray, detrend_type: str = "linear") -> np.ndarray:
    """Detrend each channel along the time axis (``-1``).

    ``detrend_type`` is ``"linear"`` (remove a least-squares linear trend) or
    ``"constant"`` (remove the mean). Deterministic.
    """
    if detrend_type not in ("linear", "constant"):
        raise ValueError(f"unsupported detrend type {detrend_type!r}")
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    if arr.shape[-1] == 0:
        return arr
    out = sp_signal.detrend(arr, axis=-1, type=detrend_type)
    return np.ascontiguousarray(out, dtype=np.float64)
