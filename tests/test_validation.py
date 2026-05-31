"""Tests for Productization P9 — Validation & Performance Assurance Program.

Exercises the validation layer over the **real** P1-P8 systems (no fake substitutes):
benchmarking, model/pipeline validation, robustness, reliability, reproducibility,
calibration, drift, scorecards, reporting, and validation integrity. A single
module-scoped full run is shared across most assertions to keep runtime reasonable.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from validation import run_validation, ReproducibilityValidator, PlatformHarness
from validation.program import _cohort_files

REPO = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def vrun(eeg_fixtures, tmp_path_factory):
    ws = tmp_path_factory.mktemp("p9_run")
    return run_validation(dict(eeg_fixtures), benchmark_runs=2, reliability_repeats=2,
                          reliability_stress=3, cross_instance=False, workspace_dir=str(ws))


# =============================================================================
# P9-B — Benchmarking
# =============================================================================
def test_benchmarks_succeed_and_are_deterministic(vrun):
    assert set(vrun["benchmarks"]) == {"pipeline", "inference", "workflow", "operational"}
    for name, result in vrun["benchmarks"].items():
        d = result.to_dict()
        assert d["success_rate"] == 1.0, name
        assert d["deterministic"], name
        assert d["latency_ms"]["count"] >= 1            # informational latency captured
        assert d["signature"]                            # auditable signature present


# =============================================================================
# P9-C — Model validation (all four architectures)
# =============================================================================
def test_all_four_architectures_evaluated(vrun):
    models = vrun["model_benchmark"]["models"]
    assert {"eegnet", "deepconvnet", "temporal_cnn", "transformer"} <= set(models)
    for arch, m in models.items():
        mt = m["metrics"]
        for key in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "ece", "brier"):
            assert key in mt, (arch, key)
        assert len(mt["confusion_matrix"]) >= 2          # confusion matrix present


# =============================================================================
# P9-D — Pipeline validation
# =============================================================================
def test_pipeline_validation(vrun):
    res = vrun["pipeline_result"]
    assert res.success and res.traceable
    assert [s.name for s in res.stages] == ["case", "ingest", "process", "features", "predict"]
    assert all(s.ok for s in res.stages)


# =============================================================================
# P9-E — Robustness
# =============================================================================
def test_robustness_graceful_and_recovers(vrun):
    rob = vrun["robustness"]
    assert rob["all_graceful"] and rob["recovered"]
    assert rob["n_cases"] >= 6
    # every degraded input was handled without raising
    assert all(not c["raised"] for c in rob["cases"])


# =============================================================================
# P9-F — Reliability
# =============================================================================
def test_reliability_all_checks_pass(vrun):
    rel = vrun["reliability"]
    assert rel["ok"]
    names = {c["name"] for c in rel["checks"]}
    assert {"repeated_execution", "long_running_execution", "stress_execution",
            "registry_integrity", "audit_integrity", "lineage_integrity",
            "workflow_integrity"} <= names
    assert all(c["passed"] for c in rel["checks"])


# =============================================================================
# Reproducibility (within + cross instance)
# =============================================================================
def test_within_instance_reproducible(vrun):
    assert vrun["reproducibility"]["within_instance"]["reproducible"]


def test_cross_instance_reproducible(eeg_fixtures, tmp_path):
    from backend.model_foundation import ModelArchitecture
    fixtures = dict(eeg_fixtures)
    harness = PlatformHarness(workspace_dir=str(tmp_path / "h0"))
    feats = harness.build_cohort(_cohort_files(fixtures))
    mut = harness.train_models(feats, [ModelArchitecture.EEGNET])["eegnet"]
    result = ReproducibilityValidator().run(
        harness, fixtures["valid.edf"], mut,
        build_harness=lambda: PlatformHarness(workspace_dir=str(tmp_path / f"h{id(object())}")),
        eeg_files=_cohort_files(fixtures), architecture=ModelArchitecture.EEGNET)
    assert result["ok"] and result["cross_instance"]["reproducible"]


# =============================================================================
# P9-G — Calibration
# =============================================================================
def test_calibration_validated(vrun):
    cal = vrun["calibration"]
    assert cal["ok"]
    for arch, m in cal["models"].items():
        assert 0.0 <= m["ece"] <= 1.0 and m["brier"] >= 0.0
    rep = cal["representative_prediction"]
    assert rep["confidence_level"] and rep["calibration_quality"]


# =============================================================================
# P9-H — Drift (measure only)
# =============================================================================
def test_drift_is_measured_not_corrected(vrun):
    drift = vrun["drift"]
    assert drift["pipeline_drift"]["stable"]                       # same input -> 0 drift
    assert drift["feature_drift"]["dims"] > 0
    assert "class_changed" in drift["prediction_drift"]
    assert "unanimous" in drift["model_consistency"]
    report = vrun["reports"]["drift_report"]
    assert "no drift correction" in report["note"]


# =============================================================================
# P9-I — Scorecards
# =============================================================================
def test_scorecards_generate(vrun):
    sc = vrun["scorecards"]
    cards = sc["scorecards"]
    expected = {"eeg_readiness", "signal_processing_readiness", "feature_engineering_readiness",
                "model_readiness", "inference_readiness", "backend_readiness", "frontend_readiness",
                "operations_readiness", "overall_product_readiness"}
    assert expected <= set(cards)
    assert sc["overall_ready"] and sc["overall_score"] == 1.0
    for name, card in cards.items():
        assert card["criteria"] and "score" in card


# =============================================================================
# P9-J — Reporting
# =============================================================================
def test_reports_and_executive_summary(vrun):
    reports = vrun["reports"]
    assert {"benchmark_report", "performance_report", "reliability_report", "robustness_report",
            "calibration_report", "drift_report", "readiness_report", "validation_summary",
            "executive_summary"} <= set(reports)
    exe = reports["executive_summary"]
    # the five questions P9 exists to answer are present
    assert {"how_accurate_are_the_models", "how_reliable_is_the_pipeline",
            "how_robust_is_the_system", "how_stable_are_predictions",
            "how_ready_is_the_product"} <= set(exe)
    assert exe["how_accurate_are_the_models"]["per_architecture"]


def test_deterministic_report_signatures(eeg_fixtures, tmp_path):
    """The deterministic (non-timing) report signatures are stable across runs."""
    a = run_validation(dict(eeg_fixtures), benchmark_runs=1, reliability_repeats=2,
                       reliability_stress=2, cross_instance=False, workspace_dir=str(tmp_path / "a"))
    b = run_validation(dict(eeg_fixtures), benchmark_runs=1, reliability_repeats=2,
                       reliability_stress=2, cross_instance=False, workspace_dir=str(tmp_path / "b"))
    assert a["scorecards"]["signature"] == b["scorecards"]["signature"]
    assert a["reports"]["validation_summary"]["signature"] == \
        b["reports"]["validation_summary"]["signature"]
    assert a["pipeline_result"].output_fingerprint() == b["pipeline_result"].output_fingerprint()


# =============================================================================
# Validation integrity + boundary
# =============================================================================
def test_validation_complete(vrun):
    assert vrun["validation_complete"]
    assert vrun["reports"]["validation_summary"]["validation_complete"]


def test_no_domain_package_imports_validation():
    for pkg in ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend",
                "operations"):
        for path in (REPO / pkg).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(a.name.split(".")[0] != "validation" for a in node.names), path
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    assert node.module.split(".")[0] != "validation", path
