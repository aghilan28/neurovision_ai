"""Tests for recording intelligence."""

from __future__ import annotations

from evaluation.dataset_intelligence.recording_analysis import analyze_recordings


def test_recording_lengths_and_variability(cohort):
    report = analyze_recordings(cohort)
    assert report.length_seconds.stats.count == 4
    assert report.distinct_sampling_rates == 2  # 256 and 200
    assert report.distinct_durations == 4


def test_mixed_sampling_rate_finding(cohort):
    report = analyze_recordings(cohort)
    assert any(f.code == "MIXED_SAMPLING_RATES" for f in report.findings)


def test_temporal_distribution_present(cohort):
    report = analyze_recordings(cohort)
    # Fixtures use start date 2002-03; expect a populated month bucket.
    keys = dict(report.temporal_distribution.counts)
    assert sum(keys.values()) == 4
