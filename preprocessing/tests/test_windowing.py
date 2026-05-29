"""Tests for deterministic window generation."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.schemas.config import WindowConfig
from preprocessing.schemas.enums import BoundaryPolicy
from preprocessing.windowing import WindowingError, generate_windows, plan_windows

FS = 100.0
CH = ("C3", "C4")


def _signal(n):
    return np.tile(np.arange(n, dtype=float), (len(CH), 1))


def test_non_overlapping_windows_count_and_shape():
    sig = _signal(1000)  # 10 s @ 100 Hz
    ws = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, overlap=0.0))
    assert ws.n_windows == 5
    assert ws.window_samples == 200
    assert ws.data.shape == (5, 2, 200)
    assert ws.windows[0].start_sample == 0
    assert ws.windows[1].start_sample == 200


def test_overlap_increases_window_count():
    sig = _signal(1000)
    ws = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, overlap=0.5))
    # step = 100 samples, last full start = 800 -> windows at 0,100,...,800 = 9
    assert ws.n_windows == 9
    assert ws.windows[1].start_sample == 100


def test_drop_policy_discards_partial_tail():
    sig = _signal(950)  # not a multiple of 200
    ws = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, boundary_policy=BoundaryPolicy.DROP))
    assert ws.n_windows == 4  # 800 samples used, last 150 dropped
    assert all(w.padded_samples == 0 for w in ws.windows)


def test_pad_policy_pads_tail():
    sig = _signal(950)
    ws = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, boundary_policy=BoundaryPolicy.PAD))
    assert ws.n_windows == 5
    last = ws.windows[-1]
    assert last.padded_samples == 50
    # Padded region is zeros.
    assert np.all(ws.data[-1, :, -50:] == 0.0)


def test_signal_shorter_than_window():
    sig = _signal(50)
    dropped = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, boundary_policy=BoundaryPolicy.DROP))
    assert dropped.n_windows == 0
    padded = generate_windows(sig, CH, FS, WindowConfig(window_seconds=2.0, boundary_policy=BoundaryPolicy.PAD))
    assert padded.n_windows == 1
    assert padded.windows[0].padded_samples == 150


@pytest.mark.determinism
def test_plan_is_deterministic():
    cfg = WindowConfig(window_seconds=2.0, overlap=0.25)
    assert plan_windows(1000, FS, cfg) == plan_windows(1000, FS, cfg)


def test_invalid_overlap_raises():
    with pytest.raises(WindowingError):
        generate_windows(_signal(1000), CH, FS, WindowConfig(window_seconds=2.0, overlap=1.0))
