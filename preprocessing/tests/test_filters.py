"""Tests for filters: behaviour, scientific correctness, and determinism."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.filters import (
    apply_bandpass,
    apply_detrend,
    apply_filter_chain,
    apply_notch,
    check_bandpass_response,
    check_notch_response,
)
from preprocessing.filters.specs import FilterDesignError, design_bandpass_sos
from preprocessing.schemas.config import FilterConfig

FS = 256.0


def _power_at(signal: np.ndarray, freq: float, fs: float) -> float:
    flat = np.asarray(signal, dtype=np.float64).reshape(-1)
    n = flat.shape[0]
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    spectrum = np.abs(np.fft.rfft(flat))
    return float(spectrum[np.argmin(np.abs(freqs - freq))])


@pytest.mark.scientific
def test_notch_suppresses_line_noise_preserves_signal():
    t = np.arange(int(FS * 8)) / FS
    sig = (np.sin(2 * np.pi * 10 * t) + np.sin(2 * np.pi * 60 * t))[np.newaxis, :]
    out, spec = apply_notch(sig, FS, 60.0, 30.0)
    assert _power_at(out, 60.0, FS) < 0.1 * _power_at(sig, 60.0, FS)
    assert _power_at(out, 10.0, FS) > 0.8 * _power_at(sig, 10.0, FS)
    assert spec.kind == "notch"


@pytest.mark.scientific
def test_bandpass_attenuates_out_of_band():
    t = np.arange(int(FS * 8)) / FS
    low = np.sin(2 * np.pi * 0.1 * t)  # below passband
    inband = np.sin(2 * np.pi * 10 * t)
    sig = (low + inband)[np.newaxis, :]
    out, _ = apply_bandpass(sig, FS, 0.5, 70.0, 4)
    assert _power_at(out, 0.1, FS) < 0.5 * _power_at(sig, 0.1, FS)
    assert _power_at(out, 10.0, FS) > 0.8 * _power_at(sig, 10.0, FS)


@pytest.mark.scientific
def test_bandpass_response_check_passes_for_defaults():
    assert check_bandpass_response(0.5, 70.0, 4, FS).passed


@pytest.mark.scientific
def test_notch_response_check_passes_for_defaults():
    assert check_notch_response(60.0, 30.0, FS).passed


def test_detrend_removes_linear_trend():
    t = np.arange(int(FS * 4)) / FS
    sig = (np.sin(2 * np.pi * 10 * t) + 5.0 * t)[np.newaxis, :]
    out = apply_detrend(sig, "linear")
    assert abs(float(np.mean(out))) < 1e-6


@pytest.mark.determinism
def test_filter_chain_is_deterministic(make_recording):
    rec = make_recording(duration_s=10.0)
    a, _ = apply_filter_chain(rec.signals, rec.sampling_rate_hz, FilterConfig())
    b, _ = apply_filter_chain(rec.signals, rec.sampling_rate_hz, FilterConfig())
    assert np.array_equal(a, b)


def test_zero_phase_preserves_length(make_recording):
    rec = make_recording(duration_s=5.0)
    out, specs = apply_filter_chain(rec.signals, rec.sampling_rate_hz, FilterConfig())
    assert out.shape == rec.signals.shape
    assert all(s.zero_phase for s in specs)


def test_bandpass_design_rejects_invalid_cutoffs():
    with pytest.raises(FilterDesignError):
        design_bandpass_sos(70.0, 0.5, 4, FS)  # low >= high
    with pytest.raises(FilterDesignError):
        design_bandpass_sos(0.5, 70.0, 4, 0.0)  # fs <= 0


def test_high_cutoff_clamped_below_nyquist():
    # Requesting 130 Hz at fs=256 (Nyquist 128) must clamp, not crash.
    _out, specs = apply_filter_chain(
        np.zeros((1, 1024)), FS, FilterConfig(bandpass_high_hz=130.0, apply_notch=False)
    )
    bp = next(s for s in specs if s.kind == "bandpass")
    assert bp.parameters["high_clamped_to_nyquist"] is True
    assert bp.parameters["effective_high_hz"] < FS / 2.0
