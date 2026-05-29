"""Tests for normalization methods."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.normalization import normalize_per_channel, normalize_per_window
from preprocessing.schemas.enums import NormalizationMethod


def test_zscore_per_channel_zero_mean_unit_std():
    rng = np.random.default_rng(0)
    sig = rng.standard_normal((4, 1000)) * 5.0 + 3.0
    out = normalize_per_channel(sig, NormalizationMethod.ZSCORE)
    assert np.allclose(out.mean(axis=1), 0.0, atol=1e-9)
    assert np.allclose(out.std(axis=1), 1.0, atol=1e-6)


def test_robust_per_channel_zero_median():
    rng = np.random.default_rng(1)
    sig = rng.standard_normal((3, 1000))
    out = normalize_per_channel(sig, NormalizationMethod.ROBUST)
    assert np.allclose(np.median(out, axis=1), 0.0, atol=1e-9)


def test_none_is_identity():
    sig = np.arange(12.0).reshape(3, 4)
    assert np.array_equal(normalize_per_channel(sig, NormalizationMethod.NONE), sig)


def test_constant_channel_does_not_divide_by_zero():
    sig = np.ones((2, 100))
    out = normalize_per_channel(sig, NormalizationMethod.ZSCORE)
    assert np.all(np.isfinite(out))


def test_per_window_normalizes_each_window():
    rng = np.random.default_rng(2)
    windows = rng.standard_normal((5, 3, 200)) * 2.0 + 1.0
    out = normalize_per_window(windows, NormalizationMethod.ZSCORE)
    assert np.allclose(out.mean(axis=-1), 0.0, atol=1e-9)
    assert np.allclose(out.std(axis=-1), 1.0, atol=1e-6)


@pytest.mark.determinism
def test_normalization_deterministic():
    sig = np.random.default_rng(3).standard_normal((4, 500))
    a = normalize_per_channel(sig, NormalizationMethod.ZSCORE)
    b = normalize_per_channel(sig, NormalizationMethod.ZSCORE)
    assert np.array_equal(a, b)
