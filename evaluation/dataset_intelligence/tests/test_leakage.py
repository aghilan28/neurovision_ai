"""Tests for dataset-level leakage-risk analysis."""

from __future__ import annotations

from evaluation.dataset_intelligence.leakage import analyze_leakage_risk
from evaluation.dataset_intelligence.tests.conftest import RecordSpec


def test_duplicate_recordings_are_critical_leakage(make_records):
    records = make_records([
        RecordSpec("dup", "P-1 M 01-JAN-1970 A"),
        RecordSpec("dup", "P-1 M 01-JAN-1970 A"),  # identical content
        RecordSpec("c", "P-2 F 01-JAN-1980 B"),
    ])
    report = analyze_leakage_risk(records)
    assert any(f.code == "DUPLICATE_RECORDINGS" and f.severity.value == "critical"
               for f in report.findings)
    assert report.leakage_risk_score > 0.0
    assert any("Deduplicate" in r for r in report.recommendations)


def test_patient_repetition_flagged(cohort):
    report = analyze_leakage_risk(cohort)
    assert any(f.code == "PATIENT_REPETITION" for f in report.findings)
    # Always recommends patient-level splitting.
    assert any("patient" in r.lower() for r in report.recommendations)


def test_clean_unique_cohort_low_risk(make_records):
    records = make_records([
        RecordSpec("a", "P-1 M 01-JAN-1970 A", start_time="01.00.00"),
        RecordSpec("b", "P-2 F 01-JAN-1980 B", start_time="02.00.00"),
        RecordSpec("c", "P-3 M 01-JAN-1990 C", start_time="03.00.00"),
    ])
    report = analyze_leakage_risk(records)
    assert report.leakage_risk_score == 0.0
    assert not any(f.severity.value == "critical" for f in report.findings)


def test_empty_dataset_zero_risk():
    report = analyze_leakage_risk([])
    assert report.leakage_risk_score == 0.0
