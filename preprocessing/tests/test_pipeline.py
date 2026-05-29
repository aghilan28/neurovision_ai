"""End-to-end pipeline tests."""

from __future__ import annotations

import numpy as np

from preprocessing.pipelines import PreprocessingPipeline
from preprocessing.schemas.config import (
    MontageConfig,
    NormalizationConfig,
    PipelineConfig,
    ResampleConfig,
    WindowConfig,
)
from preprocessing.schemas.enums import (
    MissingChannelPolicy,
    MontageType,
    NormalizationScope,
    StageName,
    StageStatus,
)
from preprocessing.schemas.signal import RawRecording


def _stage(result, name):
    return next(s for s in result.stage_results if s.stage is name)


def test_default_pipeline_produces_windows(make_recording):
    rec = make_recording(fs=200.0, duration_s=30.0)
    result = PreprocessingPipeline().run(rec)
    assert result.ok
    assert result.windows is not None
    # 30 s at target 256 Hz, 10 s windows -> 3 windows; 19 channels; 2560 samples.
    assert result.windows.data.shape == (3, 19, 2560)
    assert result.windows.sampling_rate_hz == 256.0


def test_all_stages_present_and_ordered(make_recording):
    result = PreprocessingPipeline().run(make_recording(duration_s=20.0))
    seq = [s.stage for s in result.stage_results]
    assert seq == [
        StageName.INPUT_VALIDATION, StageName.CHANNEL_VALIDATION, StageName.RESAMPLING,
        StageName.FILTERING, StageName.MONTAGE, StageName.NORMALIZATION, StageName.WINDOWING,
        StageName.OUTPUT_VALIDATION, StageName.QUALITY, StageName.LINEAGE,
    ]


def test_lineage_records_every_transform(make_recording):
    result = PreprocessingPipeline().run(make_recording(fs=200.0, duration_s=20.0))
    stages = result.lineage.stage_sequence()
    assert stages == ("resampling", "filtering", "normalization", "windowing")
    for tr in result.lineage.transformations:
        assert tr.operation_version
        assert tr.output_fingerprint
    assert result.lineage.config_fingerprint
    assert result.lineage.input_fingerprint
    assert result.lineage.output_fingerprint


def test_bipolar_montage_pipeline(make_recording):
    cfg = PipelineConfig(montage=MontageConfig(
        enabled=True, montage_type=MontageType.BIPOLAR,
        montage_name="longitudinal_bipolar_double_banana",
        missing_policy=MissingChannelPolicy.SKIP))
    result = PreprocessingPipeline(cfg).run(make_recording(duration_s=20.0))
    assert result.ok
    assert result.montage_result is not None
    assert result.windows.n_channels == len(result.montage_result.output_channels)


def test_pipeline_fails_gracefully_on_bad_input():
    rec = RawRecording(signals=np.zeros((2, 0)), channel_names=("C3", "C4"), sampling_rate_hz=256.0)
    result = PreprocessingPipeline().run(rec)
    assert result.status == "failed"
    assert _stage(result, StageName.INPUT_VALIDATION).status is StageStatus.FAILED
    assert result.windows is None


def test_pipeline_fails_on_missing_montage_channels_error_policy(make_recording):
    cfg = PipelineConfig(montage=MontageConfig(
        enabled=True, montage_type=MontageType.BIPOLAR,
        montage_name="longitudinal_bipolar_double_banana",
        missing_policy=MissingChannelPolicy.ERROR))
    rec = make_recording(channel_names=("FP1", "F7"), duration_s=10.0)
    result = PreprocessingPipeline(cfg).run(rec)
    assert result.status == "failed"
    assert _stage(result, StageName.CHANNEL_VALIDATION).status is StageStatus.FAILED


def test_per_window_normalization_scope(make_recording):
    cfg = PipelineConfig(
        normalization=NormalizationConfig(scope=NormalizationScope.PER_CHANNEL_WINDOW),
    )
    result = PreprocessingPipeline(cfg).run(make_recording(fs=256.0, duration_s=30.0))
    assert result.ok
    # Each window/channel should be ~zero-mean (normalized within window).
    means = result.windows.data.mean(axis=-1)
    assert np.allclose(means, 0.0, atol=1e-9)
    assert _stage(result, StageName.NORMALIZATION).status is StageStatus.SKIPPED


def test_disabled_windowing_returns_processed_signal(make_recording):
    cfg = PipelineConfig(windowing=WindowConfig(enabled=False))
    result = PreprocessingPipeline(cfg).run(make_recording(fs=256.0, duration_s=10.0))
    assert result.ok
    assert result.windows is None
    assert result.processed_signal is not None


def test_resampling_skipped_when_already_target(make_recording):
    cfg = PipelineConfig(resample=ResampleConfig(target_hz=256.0))
    result = PreprocessingPipeline(cfg).run(make_recording(fs=256.0, duration_s=10.0))
    assert _stage(result, StageName.RESAMPLING).status is StageStatus.SKIPPED
