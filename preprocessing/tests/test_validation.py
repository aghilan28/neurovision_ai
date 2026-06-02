"""Tests for input / channel / output validation."""

from __future__ import annotations

import numpy as np

from preprocessing.montages import get_montage
from preprocessing.schemas.signal import RawRecording
from preprocessing.validation import (
    validate_channels,
    validate_input,
    validate_output_signal,
    validate_output_windows,
)


def _rec(sig, names, fs=256.0):
    return RawRecording(signals=np.asarray(sig, dtype=float), channel_names=tuple(names),
                        sampling_rate_hz=fs)


def test_valid_input_passes(make_recording):
    assert validate_input(make_recording(duration_s=5.0)).ok


def test_zero_sample_input_fails():
    report = validate_input(_rec(np.zeros((2, 0)), ("C3", "C4")))
    assert not report.ok
    assert any(i.code == "NO_SAMPLES" for i in report.issues)


def test_bad_sampling_rate_fails():
    report = validate_input(_rec(np.zeros((2, 10)), ("C3", "C4"), fs=0.0))
    assert not report.ok
    assert any(i.code == "INVALID_SAMPLING_RATE" for i in report.issues)


def test_channel_validation_missing_required():
    rec = _rec(np.zeros((2, 100)), ("FP1", "F7"))
    report = validate_channels(rec, get_montage("longitudinal_bipolar_double_banana"))
    assert not report.ok
    assert any(i.code == "MISSING_REQUIRED_CHANNELS" for i in report.issues)


def test_output_signal_nonfinite_fails():
    sig = np.zeros((2, 10))
    sig[0, 0] = np.nan
    report = validate_output_signal(sig, 2)
    assert not report.ok
    assert any(i.code == "NONFINITE_OUTPUT" for i in report.issues)


def test_output_windows_shape_consistency(make_recording):
    from preprocessing.schemas.config import WindowConfig
    from preprocessing.windowing import generate_windows

    rec = make_recording(duration_s=20.0)
    ws = generate_windows(rec.signals, rec.channel_names, rec.sampling_rate_hz, WindowConfig())
    assert validate_output_windows(ws).ok
