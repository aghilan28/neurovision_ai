"""Zero-phase Butterworth bandpass filtering."""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal

from preprocessing.filters.specs import bandpass_spec, design_bandpass_sos
from preprocessing.schemas.reports import FilterSpec


def apply_bandpass(
    signals: np.ndarray,
    sampling_rate_hz: float,
    low_hz: float,
    high_hz: float,
    order: int,
) -> tuple[np.ndarray, FilterSpec]:
    """Apply a zero-phase Butterworth bandpass to each channel (axis ``-1``).

    Uses ``sosfiltfilt`` (forward-backward) for zero phase distortion — important
    for preserving the morphology of clinical waveforms. Deterministic given fixed
    parameters and sampling rate.
    """
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    sos = design_bandpass_sos(low_hz, high_hz, order, sampling_rate_hz)
    if arr.shape[-1] == 0:
        return arr, bandpass_spec(low_hz, high_hz, order, sampling_rate_hz)
    filtered = sp_signal.sosfiltfilt(sos, arr, axis=-1)
    return np.ascontiguousarray(filtered, dtype=np.float64), bandpass_spec(
        low_hz, high_hz, order, sampling_rate_hz
    )
