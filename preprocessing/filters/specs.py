"""Filter design helpers and specifications.

Centralizes the SciPy filter *design* (coefficients) and the construction of
:class:`~preprocessing.schemas.reports.FilterSpec` records. Designs are pure
functions of their parameters + sampling rate, so they are deterministic and
fingerprintable.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal

from preprocessing.schemas.reports import FilterSpec

#: Version of the filter operations (recorded on lineage/specs).
FILTER_OP_VERSION = "1.0.0"


class FilterDesignError(ValueError):
    """Raised when a filter cannot be designed for the given parameters/rate."""


def _nyquist(fs: float) -> float:
    return fs / 2.0


def _effective_high(high_hz: float, fs: float) -> tuple[float, bool]:
    """Clamp the high cutoff below Nyquist; report whether clamping occurred.

    Clamping is recorded in the FilterSpec (never hidden); it keeps the design
    valid when an upstream choice (e.g. a low resample rate) would otherwise place
    the requested cutoff at/above Nyquist.
    """
    nyq = _nyquist(fs)
    limit = 0.99 * nyq
    if high_hz >= limit:
        return limit, True
    return high_hz, False


def design_bandpass_sos(low_hz: float, high_hz: float, order: int, fs: float) -> np.ndarray:
    """Design a Butterworth bandpass as second-order sections (SOS)."""
    if fs <= 0:
        raise FilterDesignError(f"sampling rate must be positive, got {fs}")
    if low_hz <= 0:
        raise FilterDesignError(f"bandpass low cutoff must be > 0, got {low_hz}")
    eff_high, _ = _effective_high(high_hz, fs)
    if low_hz >= eff_high:
        raise FilterDesignError(
            f"bandpass low cutoff {low_hz} must be below the (effective) high cutoff {eff_high}"
        )
    if order < 1:
        raise FilterDesignError(f"filter order must be >= 1, got {order}")
    return sp_signal.butter(
        order, [low_hz, eff_high], btype="band", fs=fs, output="sos"
    )


def design_notch_sos(freq_hz: float, q: float, fs: float) -> np.ndarray:
    """Design an IIR notch filter (as SOS) at ``freq_hz``."""
    if fs <= 0:
        raise FilterDesignError(f"sampling rate must be positive, got {fs}")
    if not (0 < freq_hz < _nyquist(fs)):
        raise FilterDesignError(
            f"notch frequency {freq_hz} must be in (0, Nyquist={_nyquist(fs)})"
        )
    if q <= 0:
        raise FilterDesignError(f"notch Q must be > 0, got {q}")
    b, a = sp_signal.iirnotch(w0=freq_hz, Q=q, fs=fs)
    return sp_signal.tf2sos(b, a)


def bandpass_spec(low_hz: float, high_hz: float, order: int, fs: float) -> FilterSpec:
    eff_high, clamped = _effective_high(high_hz, fs)
    return FilterSpec(
        kind="bandpass",
        description=(
            f"Butterworth bandpass {low_hz}-{eff_high} Hz, order {order}, zero-phase "
            f"(sosfiltfilt)"
        ),
        parameters={
            "low_hz": low_hz,
            "high_hz": high_hz,
            "effective_high_hz": eff_high,
            "high_clamped_to_nyquist": clamped,
            "order": order,
            "design": "butterworth_sos",
            "application": "sosfiltfilt",
        },
        sampling_rate_hz=fs,
        zero_phase=True,
    )


def notch_spec(freq_hz: float, q: float, fs: float) -> FilterSpec:
    return FilterSpec(
        kind="notch",
        description=f"IIR notch at {freq_hz} Hz, Q={q}, zero-phase (sosfiltfilt)",
        parameters={
            "freq_hz": freq_hz,
            "q": q,
            "design": "iirnotch_sos",
            "application": "sosfiltfilt",
        },
        sampling_rate_hz=fs,
        zero_phase=True,
    )


def detrend_spec(detrend_type: str, fs: float) -> FilterSpec:
    return FilterSpec(
        kind="detrend",
        description=f"{detrend_type} detrend (baseline-drift removal)",
        parameters={"type": detrend_type, "application": "scipy.signal.detrend"},
        sampling_rate_hz=fs,
        zero_phase=True,
    )
