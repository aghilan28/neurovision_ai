"""Tests for dataset quality scoring."""

from __future__ import annotations

from evaluation.dataset_intelligence.quality_analysis import analyze_quality
from evaluation.dataset_intelligence.tests.conftest import RecordSpec


def test_clean_cohort_high_score(cohort):
    report = analyze_quality(cohort)
    assert 0.0 <= report.quality_score <= 1.0
    assert report.quality_score > 0.9
    assert report.counts["total_records"] == 4


def test_duplicate_recordings_detected(make_records):
    # Two identical specs -> identical content hash -> duplicate recording.
    records = make_records([
        RecordSpec("dup", "P-1 M 01-JAN-1970 A"),
        RecordSpec("dup", "P-1 M 01-JAN-1970 A"),
        RecordSpec("c", "P-2 F 01-JAN-1980 B"),
    ])
    report = analyze_quality(records)
    assert report.counts["duplicate_recordings"] >= 1
    assert any(f.code == "DUPLICATE_RECORDINGS" for f in report.findings)
    assert report.component_scores["uniqueness"] < 1.0


def test_empty_dataset():
    report = analyze_quality([])
    assert report.quality_score == 0.0
    assert any(f.code == "EMPTY_DATASET" for f in report.findings)


def test_quality_is_report_only_does_not_mutate(cohort):
    before = [r.to_dict() for r in cohort]
    analyze_quality(cohort)
    after = [r.to_dict() for r in cohort]
    assert before == after
