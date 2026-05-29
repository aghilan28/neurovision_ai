"""End-to-end pipeline tests: the full required deliverable with traceability.

Verifies the complete chain executes and that the whole run is reproducible:
  Dataset -> Preprocessing -> Patient-Disjoint Split -> Baseline Model ->
  Evaluation -> Calibration -> Conformal -> Coverage -> Risk -> Benchmark.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from datasets import SyntheticConfig, SplitConfig
from ml.training import TrainingConfig
from scripts.run_pipeline import run_pipeline, PipelineConfig


def _small_config(output_dir) -> PipelineConfig:
    return PipelineConfig(
        synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
        split=SplitConfig(),
        training=TrainingConfig(steps=80),
        models=("simple_cnn", "eegnet", "tcn"),
        alpha=0.1,
        output_dir=str(output_dir),
    )


@pytest.fixture(scope="module")
def pipeline_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    return run_pipeline(_small_config(out), verbose=False)


def test_all_three_models_complete_full_chain(pipeline_result):
    summary = pipeline_result["pipeline_summary"]
    assert set(summary["models"]) == {"simple_cnn", "eegnet", "tcn"}
    for name, m in summary["models"].items():
        assert m["status"] == "registered"
        assert m["patient_disjoint"] is True
        assert m["training_validation_ok"] is True
        assert m["uncertainty_validation_ok"] is True
        assert m["clinical_prediction_complete"] is True
        assert m["coverage"]["reliable"] is True
        assert m["coverage"]["observed"] >= m["coverage"]["target"] - 0.1
        # full lineage chain present
        assert set(m["lineage"]) == {"training", "evaluation", "uncertainty", "benchmark"}


def test_registries_and_artifacts_written(pipeline_result):
    store = pipeline_result["store"]
    assert store.verify() is True  # all artifact checksums valid
    root = pathlib.Path(store.root)
    for rel in ["registries/model_registry.json", "registries/benchmark_registry.json",
                "registries/uncertainty_registry.json", "registries/lineage.json",
                "pipeline_summary.json"]:
        assert (root / rel).exists()
    # each model wrote the six uncertainty reports
    mr = json.loads((root / "registries/model_registry.json").read_text())
    assert mr["n_models"] == 3
    for model_version in mr["models"]:
        name = mr["models"][model_version]["model_name"]
        base = root / name / model_version / "reports"
        for report in ["calibration_report", "conformal_report", "coverage_report",
                       "risk_report", "summary_report", "audit_report"]:
            assert (base / f"{report}.json").exists()


def test_benchmark_registry_has_three_models(pipeline_result):
    breg = pipeline_result["benchmark_registry"]
    assert len(breg.list_benchmarks()) == 3
    lb = breg.leaderboard("macro_f1")
    assert all(row["macro_f1"] is not None for row in lb)


def test_audit_report_is_traceable(pipeline_result):
    store = pipeline_result["store"]
    root = pathlib.Path(store.root)
    mr = json.loads((root / "registries/model_registry.json").read_text())
    model_version = next(iter(mr["models"]))
    name = mr["models"][model_version]["model_name"]
    audit = json.loads((root / name / model_version / "reports/audit_report.json").read_text())
    assert audit["traceable"] is True
    assert audit["lineage_chain"]  # full chain recorded
    assert audit["validation"]["training"]["ok"] is True
    assert audit["validation"]["uncertainty"]["ok"] is True


def test_pipeline_is_reproducible(tmp_path):
    r1 = run_pipeline(_small_config(tmp_path / "a"), verbose=False)
    r2 = run_pipeline(_small_config(tmp_path / "b"), verbose=False)
    assert r1["run_id"] == r2["run_id"]
    assert r1["summary_checksum"] == r2["summary_checksum"]
    assert sorted(r1["benchmark_registry"].list_benchmarks()) == \
           sorted(r2["benchmark_registry"].list_benchmarks())
