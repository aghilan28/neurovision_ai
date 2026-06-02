"""Tests for the report-only signal-quality subsystem."""

from __future__ import annotations

import numpy as np

from preprocessing.quality import QualityThresholds, assess_quality

FS = 256.0
CH = ("C3", "C4", "O1")


def _codes(report):
    return {i.code for i in report.issues}


def test_flat_channel_detected():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    sig[1, :] = 0.0  # flat channel
    report = assess_quality(sig, CH, FS)
    assert "FLAT_CHANNEL" in _codes(report)
    assert "C4" in report.flagged_channels


def test_invalid_channel_all_nonfinite_is_critical():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    sig[0, :] = np.nan
    report = assess_quality(sig, CH, FS)
    assert "INVALID_CHANNEL" in _codes(report)
    assert report.has_critical


def test_partial_nonfinite_is_corrupted_segment():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    sig[2, 10:20] = np.inf
    report = assess_quality(sig, CH, FS)
    assert "NONFINITE_SAMPLES" in _codes(report)


def test_high_amplitude_flagged():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    sig[0, 5] = 10_000.0
    report = assess_quality(sig, CH, FS, thresholds=QualityThresholds(amplitude_uv=500.0))
    assert "HIGH_AMPLITUDE" in _codes(report)


def test_line_noise_flagged():
    t = np.arange(int(FS * 4)) / FS
    sig = np.stack([60.0 * np.sin(2 * np.pi * 60 * t) for _ in range(3)])  # pure mains
    report = assess_quality(sig, CH, FS, thresholds=QualityThresholds(mains_hz=60.0, mains_ratio=0.5))
    assert "LINE_NOISE" in _codes(report)


def test_missing_channel_reported():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    report = assess_quality(sig, CH, FS, expected_channels=("C3", "PZ"))
    assert "MISSING_CHANNEL" in _codes(report)


def test_quality_never_mutates_signal():
    sig = np.random.default_rng(0).standard_normal((3, 1000))
    before = sig.copy()
    assess_quality(sig, CH, FS)
    assert np.array_equal(sig, before)  # report-only


def test_clipping_run_flagged():
    sig = np.random.default_rng(0).standard_normal((1, 1000))
    sig[0, 100:200] = 250.0  # 100-sample constant run (clipping)
    report = assess_quality(sig, ("C3",), FS, thresholds=QualityThresholds(clipping_run=50))
    assert "CLIPPING_RUN" in _codes(report)
