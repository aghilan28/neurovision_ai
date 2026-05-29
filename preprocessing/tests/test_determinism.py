"""Determinism & reproducibility guarantees for the DSP layer (AP-3/AP-6, NR-9/NR-10)."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing._canonical import canonical_json
from preprocessing.pipelines import PreprocessingPipeline
from preprocessing.schemas.config import PipelineConfig


@pytest.mark.determinism
def test_pipeline_outputs_byte_identical_across_runs(make_recording):
    rec = make_recording(fs=200.0, duration_s=30.0)
    a = PreprocessingPipeline().run(rec)
    b = PreprocessingPipeline().run(rec)
    assert np.array_equal(a.windows.data, b.windows.data)
    assert a.lineage.output_fingerprint == b.lineage.output_fingerprint


@pytest.mark.reproducibility
def test_result_serialization_is_stable(make_recording):
    rec = make_recording(fs=200.0, duration_s=20.0)
    a = PreprocessingPipeline().run(rec)
    b = PreprocessingPipeline().run(rec)
    assert canonical_json(a.to_dict()) == canonical_json(b.to_dict())


@pytest.mark.reproducibility
def test_same_config_same_fingerprint():
    assert PipelineConfig().config_fingerprint == PipelineConfig().config_fingerprint


@pytest.mark.reproducibility
def test_different_config_different_fingerprint():
    from preprocessing.schemas.config import WindowConfig

    base = PipelineConfig()
    changed = PipelineConfig(windowing=WindowConfig(window_seconds=5.0))
    assert base.config_fingerprint != changed.config_fingerprint


@pytest.mark.determinism
def test_output_fingerprint_changes_with_input(make_recording):
    r1 = PreprocessingPipeline().run(make_recording(fs=256.0, duration_s=20.0, base_freq=10.0))
    r2 = PreprocessingPipeline().run(make_recording(fs=256.0, duration_s=20.0, base_freq=12.0))
    assert r1.lineage.output_fingerprint != r2.lineage.output_fingerprint
