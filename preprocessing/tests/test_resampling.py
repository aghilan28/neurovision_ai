"""Tests for resampling: correctness, anti-aliasing, determinism."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.resampling import ResampleError, resample_signal


def test_resample_changes_length_proportionally():
    fs_in, fs_out = 200.0, 256.0
    n = int(fs_in * 10)
    sig = np.random.default_rng(0).standard_normal((4, n))
    out, info = resample_signal(sig, fs_in, fs_out)
    assert info["changed"]
    assert abs(out.shape[-1] / n - fs_out / fs_in) < 0.01
    assert info["up"] > 0 and info["down"] > 0


def test_equal_rates_is_noop():
    sig = np.ones((2, 100))
    out, info = resample_signal(sig, 256.0, 256.0)
    assert not info["changed"]
    assert np.array_equal(out, sig)


@pytest.mark.scientific
def test_anti_aliasing_suppresses_above_new_nyquist():
    # A 90 Hz tone sampled at 256 Hz, downsampled to 128 Hz (new Nyquist 64 Hz),
    # must be strongly attenuated rather than aliased back into band.
    fs_in, fs_out = 256.0, 128.0
    t = np.arange(int(fs_in * 8)) / fs_in
    sig = np.sin(2 * np.pi * 90 * t)[np.newaxis, :]
    out, _ = resample_signal(sig, fs_in, fs_out)
    energy = float(np.sqrt(np.mean(out**2)))
    assert energy < 0.2  # tone removed by the polyphase anti-alias filter


@pytest.mark.determinism
def test_resample_is_deterministic():
    sig = np.random.default_rng(1).standard_normal((3, 2000))
    a, _ = resample_signal(sig, 200.0, 256.0)
    b, _ = resample_signal(sig, 200.0, 256.0)
    assert np.array_equal(a, b)


def test_invalid_rates_raise():
    with pytest.raises(ResampleError):
        resample_signal(np.ones((1, 10)), 0.0, 256.0)
    with pytest.raises(ResampleError):
        resample_signal(np.ones((1, 10)), 256.0, 256.0, method="fourier")
