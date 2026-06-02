"""Tests for channel inventory & compatibility."""

from __future__ import annotations

from evaluation.dataset_intelligence.channel_analysis import analyze_channels


def test_inventory_and_common_channels(cohort):
    report = analyze_channels(cohort)
    labels = {e.label for e in report.inventory}
    assert {"FP1", "C3", "O1"} <= labels
    # FP1/C3/O1 are present in all 4 recordings; FP2/C4/O2 only in three.
    assert set(report.common_channels) == {"FP1", "C3", "O1"}
    fp1 = next(e for e in report.inventory if e.label == "FP1")
    assert fp1.occurrence_count == 4
    assert fp1.availability_fraction == 1.0


def test_montage_compatibility_reported(cohort):
    report = analyze_channels(cohort)
    assert "longitudinal_bipolar_double_banana" in report.montage_compatibility
    info = report.montage_compatibility["longitudinal_bipolar_double_banana"]
    assert "compatible_fraction" in info
    assert "required_channels_missing_somewhere" in info


def test_heterogeneous_configs_finding(cohort):
    report = analyze_channels(cohort)
    assert any(f.code == "HETEROGENEOUS_CHANNEL_CONFIGS" for f in report.findings)
