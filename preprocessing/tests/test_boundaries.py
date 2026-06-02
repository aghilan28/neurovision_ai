"""Boundary-condition tests and the module-boundary (leaf purity) invariant."""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from preprocessing.pipelines import PreprocessingPipeline
from preprocessing.schemas.config import PipelineConfig, ResampleConfig, WindowConfig
from preprocessing.schemas.signal import RawRecording

# Layers preprocessing must never import (docs/architecture/IMPORT_RULES.md, NR-8).
_FORBIDDEN = ("datasets", "ml", "evaluation", "backend", "frontend", "monitoring", "deployment")
_PREPROCESSING_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.boundary
def test_preprocessing_imports_no_internal_module():
    offenders: list[str] = []
    for path in _PREPROCESSING_ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for layer in _FORBIDDEN:
            if f"import {layer}" in text or f"from {layer}" in text:
                offenders.append(f"{path.name}: imports {layer}")
    assert not offenders, f"preprocessing must be a pure leaf; found: {offenders}"


def _rec(n_ch, n_samp, fs=256.0):
    sig = np.random.default_rng(0).standard_normal((n_ch, n_samp))
    names = tuple(f"CH{i}" for i in range(n_ch))
    return RawRecording.create(sig, names, fs)


def test_single_channel_recording_processes():
    cfg = PipelineConfig()  # montage disabled by default
    result = PreprocessingPipeline(cfg).run(_rec(1, 256 * 12))
    assert result.ok
    assert result.windows.n_channels == 1


def test_recording_shorter_than_one_window_drops_to_zero(make_recording):
    cfg = PipelineConfig(resample=ResampleConfig(enabled=False),
                         windowing=WindowConfig(window_seconds=10.0))
    rec = make_recording(fs=256.0, duration_s=3.0)  # < 10 s
    result = PreprocessingPipeline(cfg).run(rec)
    assert result.ok
    assert result.windows.n_windows == 0


def test_exactly_one_window():
    cfg = PipelineConfig(resample=ResampleConfig(enabled=False),
                         windowing=WindowConfig(window_seconds=10.0))
    result = PreprocessingPipeline(cfg).run(_rec(2, 256 * 10))
    assert result.windows.n_windows == 1


def test_high_overlap_boundary():
    cfg = PipelineConfig(resample=ResampleConfig(enabled=False),
                         windowing=WindowConfig(window_seconds=2.0, overlap=0.9))
    result = PreprocessingPipeline(cfg).run(_rec(2, 256 * 10))
    assert result.ok
    assert result.windows.n_windows > 10  # dense overlap yields many windows
