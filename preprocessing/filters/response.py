"""Frequency-response validation for designed filters.

Verifies that a designed filter actually behaves as specified by probing its
magnitude response at characteristic frequencies. This turns "the filter is
correct" into an executable, recorded assertion (scientific-correctness testing,
AP-3/AP-6).

Note on zero-phase application: the pipeline applies filters with ``sosfiltfilt``
(forward-backward), which squares the magnitude response. These checks validate the
*single-pass design* response (``sosfreqz``); the effective applied attenuation is
therefore at least as strong as reported.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal

from preprocessing.filters.specs import design_bandpass_sos, design_notch_sos
from preprocessing.schemas.reports import FrequencyResponseCheck

# Acceptance thresholds (single-pass design response).
_PASSBAND_MIN_DB = -3.0  # passband must not be attenuated more than this
_STOPBAND_MAX_DB = -3.0  # stopband must be attenuated at least this much
_NOTCH_MIN_DEPTH_DB = -20.0  # the notch must be at least this deep at the target freq


def _magnitude_db(sos: np.ndarray, freqs_hz: np.ndarray, fs: float) -> np.ndarray:
    worN = 2 * np.pi * freqs_hz / fs
    _, h = sp_signal.sosfreqz(sos, worN=worN)
    mag = np.abs(h)
    return 20.0 * np.log10(np.maximum(mag, 1e-12))


def check_bandpass_response(
    low_hz: float, high_hz: float, order: int, fs: float
) -> FrequencyResponseCheck:
    """Validate a bandpass design: passband ~flat, stopbands attenuated."""
    sos = design_bandpass_sos(low_hz, high_hz, order, fs)
    nyq = fs / 2.0
    eff_high = min(high_hz, 0.99 * nyq)
    center = float(np.sqrt(low_hz * eff_high))

    probes = {"center": center, "low_stop": low_hz / 2.0}
    notes: list[str] = []

    # Probe a high stopband frequency only if there is enough separation below Nyquist.
    high_stop = min(eff_high * 2.0, 0.95 * nyq)
    check_high = high_stop > eff_high * 1.3
    if check_high:
        probes["high_stop"] = high_stop
    else:
        notes.append("high stopband probe skipped (insufficient separation below Nyquist)")

    freqs = np.array(list(probes.values()), dtype=np.float64)
    db = _magnitude_db(sos, freqs, fs)
    measured = {name: float(val) for name, val in zip(probes, db, strict=True)}

    passed = measured["center"] >= _PASSBAND_MIN_DB
    passed = passed and measured["low_stop"] <= _STOPBAND_MAX_DB
    if check_high:
        passed = passed and measured["high_stop"] <= _STOPBAND_MAX_DB

    return FrequencyResponseCheck(
        kind="bandpass",
        passed=bool(passed),
        measured_db={f"{probes[k]:.4f}Hz:{k}": v for k, v in measured.items()},
        notes=tuple(notes),
    )


def check_notch_response(freq_hz: float, q: float, fs: float) -> FrequencyResponseCheck:
    """Validate a notch design: deep at target, ~unity in nearby passband."""
    sos = design_notch_sos(freq_hz, q, fs)
    nyq = fs / 2.0
    near_low = max(freq_hz * 0.5, 0.1)
    near_high = min(freq_hz * 1.5, 0.95 * nyq)
    freqs = np.array([freq_hz, near_low, near_high], dtype=np.float64)
    db = _magnitude_db(sos, freqs, fs)
    measured = {
        "notch": float(db[0]),
        "near_low": float(db[1]),
        "near_high": float(db[2]),
    }
    passed = (
        measured["notch"] <= _NOTCH_MIN_DEPTH_DB
        and measured["near_low"] >= _PASSBAND_MIN_DB
        and measured["near_high"] >= _PASSBAND_MIN_DB
    )
    return FrequencyResponseCheck(
        kind="notch",
        passed=bool(passed),
        measured_db={
            f"{freq_hz:.4f}Hz:notch": measured["notch"],
            f"{near_low:.4f}Hz:near_low": measured["near_low"],
            f"{near_high:.4f}Hz:near_high": measured["near_high"],
        },
    )
