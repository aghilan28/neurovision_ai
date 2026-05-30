"""Deterministic EEG filtering engine (P2-C).

Real digital filters implemented with ``scipy.signal`` (zero-phase, IIR
Butterworth + IIR notch) so they are deterministic, reproducible, and stable on
short recordings. Every operation is a pure function of (data, params): it returns
a *new* array (never mutates its input) plus the ``FilterConfig`` that produced it,
so the filter configuration and history are fully tracked.

Conventions: ``data`` is a float64 array shaped ``(n_channels, n_samples)``;
frequencies are in Hz; filters are applied per channel. No randomness, no learned
state — the same input + params always yield the same output.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt

from ..models.domain import FilterConfig, FilterType
from ..version import SIGNAL_FILTERING_VERSION


class FilteringError(ValueError):
    """Raised on an invalid filter request (e.g. cutoff >= Nyquist)."""


def _check(data: np.ndarray, sfreq: float) -> None:
    if data.ndim != 2:
        raise FilteringError("data must be 2-D (n_channels, n_samples)")
    if not np.isfinite(sfreq) or sfreq <= 0:
        raise FilteringError(f"invalid sampling frequency {sfreq!r}")


def _safe_padlen(n_samples: int, default: int) -> int:
    # filtfilt/sosfiltfilt require padlen < n_samples; clamp for short recordings.
    return int(min(default, max(0, n_samples - 1)))


class FilteringEngine:
    """Stateless collection of deterministic filters."""

    version = SIGNAL_FILTERING_VERSION

    def bandpass(self, data: np.ndarray, sfreq: float, low: float, high: float,
                 order: int = 4) -> tuple[np.ndarray, FilterConfig]:
        _check(data, sfreq)
        nyq = sfreq / 2.0
        if not (0 < low < high < nyq):
            raise FilteringError(f"bandpass requires 0 < low < high < Nyquist ({nyq})")
        sos = butter(order, [low / nyq, high / nyq], btype="bandpass", output="sos")
        out = self._sos(sos, data)
        return out, FilterConfig(FilterType.BANDPASS,
                                 {"low_hz": float(low), "high_hz": float(high), "order": int(order)})

    def highpass(self, data: np.ndarray, sfreq: float, cutoff: float,
                 order: int = 4) -> tuple[np.ndarray, FilterConfig]:
        _check(data, sfreq)
        nyq = sfreq / 2.0
        if not (0 < cutoff < nyq):
            raise FilteringError(f"highpass requires 0 < cutoff < Nyquist ({nyq})")
        sos = butter(order, cutoff / nyq, btype="highpass", output="sos")
        out = self._sos(sos, data)
        return out, FilterConfig(FilterType.HIGHPASS, {"cutoff_hz": float(cutoff), "order": int(order)})

    def lowpass(self, data: np.ndarray, sfreq: float, cutoff: float,
                order: int = 4) -> tuple[np.ndarray, FilterConfig]:
        _check(data, sfreq)
        nyq = sfreq / 2.0
        if not (0 < cutoff < nyq):
            raise FilteringError(f"lowpass requires 0 < cutoff < Nyquist ({nyq})")
        sos = butter(order, cutoff / nyq, btype="lowpass", output="sos")
        out = self._sos(sos, data)
        return out, FilterConfig(FilterType.LOWPASS, {"cutoff_hz": float(cutoff), "order": int(order)})

    def notch(self, data: np.ndarray, sfreq: float, freq: float,
              quality: float = 30.0) -> tuple[np.ndarray, FilterConfig]:
        _check(data, sfreq)
        nyq = sfreq / 2.0
        if not (0 < freq < nyq):
            raise FilteringError(f"notch requires 0 < freq < Nyquist ({nyq})")
        b, a = iirnotch(freq / nyq, quality)
        padlen = _safe_padlen(data.shape[1], 3 * max(len(a), len(b)))
        out = filtfilt(b, a, data, axis=1, padlen=padlen)
        return out, FilterConfig(FilterType.NOTCH, {"freq_hz": float(freq), "quality": float(quality)})

    def reference(self, data: np.ndarray, method: str = "average") -> tuple[np.ndarray, FilterConfig]:
        if data.ndim != 2:
            raise FilteringError("data must be 2-D (n_channels, n_samples)")
        if method != "average":
            raise FilteringError(f"unsupported reference method {method!r}")
        out = data - data.mean(axis=0, keepdims=True)
        return out, FilterConfig(FilterType.REFERENCE, {"method": method})

    # --- internal --------------------------------------------------------------
    @staticmethod
    def _sos(sos: np.ndarray, data: np.ndarray) -> np.ndarray:
        padlen = _safe_padlen(data.shape[1], 3 * sos.shape[0] * 2)
        return sosfiltfilt(sos, data, axis=1, padlen=padlen)
