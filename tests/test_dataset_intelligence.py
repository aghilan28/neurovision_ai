"""Tests for the dataset-intelligence surface (V1-P3 integration)."""

from __future__ import annotations

from datasets import analyze, leakage_analysis, evaluation_readiness


def test_intelligence_report_structure(dataset, split):
    rep = analyze(dataset, split).to_dict()
    for key in ("profile", "patient_profile", "channel_profile", "quality_analysis",
                "leakage_analysis", "evaluation_readiness", "intelligence_version"):
        assert key in rep
    assert rep["profile"]["n_patients"] == len(dataset.patients())
    assert rep["channel_profile"]["n_channels"] == dataset.n_channels


def test_intelligence_is_deterministic(dataset, split):
    assert analyze(dataset, split).signature() == analyze(dataset, split).signature()


def test_leakage_analysis_flags_disjoint(dataset, split):
    leak = leakage_analysis(dataset, split)
    assert leak["patient_disjoint"] is True
    assert leak["split_present"] is True


def test_leakage_without_split_is_not_disjoint(dataset):
    leak = leakage_analysis(dataset, None)
    assert leak["patient_disjoint"] is False
    assert leak["split_present"] is False


def test_evaluation_readiness_ready(dataset, split):
    rd = evaluation_readiness(dataset, split)
    assert rd["ready"] is True
    assert 0.0 <= rd["readiness_score"] <= 1.0
    assert all(c["passed"] for c in rd["checks"])


def test_quality_analysis_clean_synthetic(dataset):
    from datasets import quality_analysis
    q = quality_analysis(dataset)
    assert q["passed"] is True
    assert q["n_with_nan"] == 0 and q["n_with_inf"] == 0
