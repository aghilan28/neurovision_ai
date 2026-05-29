"""Zero-phase IIR notch filtering (mains-interference removal)."""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal

from preprocessing.filters.specs import design_notch_sos, notch_spec
from preprocessing.schemas.reports import FilterSpec


def apply_notch(
    signals: np.ndarray,
    sampling_rate_hz: float,
    freq_hz: float,
    q: float,
) -> tuple[np.ndarray, FilterSpec]:
    """Apply a zero-phase IIR notch at ``freq_hz`` to each channel (axis ``-1``)."""
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    sos = design_notch_sos(freq_hz, q, sampling_rate_hz)
    if arr.shape[-1] == 0:
        return arr, notch_spec(freq_hz, q, sampling_rate_hz)
    filtered = sp_signal.sosfiltfilt(sos, arr, axis=-1)
    return np.ascontiguousarray(filtered, dtype=np.float64), notch_spec(
        freq_hz, q, sampling_rate_hz
    )
