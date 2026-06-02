"""Tests for artifact persistence and reporting."""

from __future__ import annotations

import json
import os

import numpy as np

from preprocessing.artifacts import build_artifact_report, write_artifacts
from preprocessing.pipelines import PreprocessingPipeline


def test_build_report_summarizes_run(make_recording):
    result = PreprocessingPipeline().run(make_recording(fs=200.0, duration_s=20.0))
    report = build_artifact_report(result)
    assert report.output_kind == "windows"
    assert report.n_windows == result.windows.n_windows
    assert report.output_fingerprint == result.windows.fingerprint()


def test_write_artifacts_roundtrip(make_recording, tmp_path):
    result = PreprocessingPipeline().run(make_recording(fs=200.0, duration_s=20.0))
    report = write_artifacts(result, tmp_path)
    assert os.path.exists(report.array_path)
    assert os.path.exists(report.manifest_path)

    loaded = np.load(report.array_path, allow_pickle=True)
    assert np.array_equal(loaded["windows"], result.windows.data)

    with open(report.manifest_path) as handle:
        manifest = json.load(handle)
    assert manifest["artifact_report"]["output_fingerprint"] == result.windows.fingerprint()
    assert manifest["result"]["lineage"]["pipeline_version"]


def test_manifest_is_deterministic(make_recording, tmp_path):
    result = PreprocessingPipeline().run(make_recording(fs=200.0, duration_s=20.0))
    write_artifacts(result, tmp_path)
    first = (tmp_path / "manifest.json").read_bytes()
    write_artifacts(result, tmp_path)
    assert (tmp_path / "manifest.json").read_bytes() == first
