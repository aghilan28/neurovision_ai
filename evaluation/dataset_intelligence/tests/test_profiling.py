"""Tests for dataset profiling."""

from __future__ import annotations

from evaluation.dataset_intelligence.profiling import profile_dataset


def test_profile_counts(cohort):
    profile = profile_dataset(cohort, dataset_id="ds", dataset_version="v1")
    assert profile.n_recordings == 4
    assert profile.n_patients == 3  # P-1 contributes two recordings
    assert profile.n_sessions == 4
    assert profile.dataset_size_bytes > 0
    assert profile.duration_stats.stats.total == 20.0 + 30.0 + 15.0 + 25.0


def test_profile_sampling_and_channel_configs(cohort):
    profile = profile_dataset(cohort)
    sr = dict(profile.sampling_frequency_distribution.counts)
    assert sr["256"] == 3
    assert sr["200"] == 1
    # Two distinct channel configurations (6-channel set vs the 3-channel one).
    assert profile.channel_configuration_distribution.n_categories == 2


def test_profile_annotation_coverage(cohort):
    profile = profile_dataset(cohort)
    cov = profile.annotation_coverage
    assert cov["records_with_annotations"] == 3
    assert cov["total_annotations"] == 4
    assert 0.0 < cov["fraction_with_annotations"] <= 1.0


def test_profile_is_reproducible(cohort):
    a = profile_dataset(cohort, dataset_version="v1", generated_at="t1")
    b = profile_dataset(cohort, dataset_version="v1", generated_at="t2-different")
    # Timestamp excluded from fingerprint -> identical.
    assert a.content_fingerprint == b.content_fingerprint


def test_empty_dataset_profile():
    profile = profile_dataset([])
    assert profile.n_recordings == 0
    assert profile.n_patients == 0
    assert profile.duration_stats.stats.count == 0
