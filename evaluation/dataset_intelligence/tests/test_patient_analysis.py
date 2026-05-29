"""Tests for patient intelligence."""

from __future__ import annotations

from evaluation.dataset_intelligence.patient_analysis import analyze_patients
from evaluation.dataset_intelligence.tests.conftest import RecordSpec


def test_patient_counts_and_repetition(cohort):
    report = analyze_patients(cohort)
    assert report.n_patients == 3
    assert report.patients_with_multiple_recordings == 1  # P-1
    assert report.max_recordings_for_single_patient == 2
    assert report.recordings_per_patient.stats.maximum == 2


def test_split_ready_when_enough_patients(cohort):
    report = analyze_patients(cohort)
    assert report.split_ready is True


def test_not_split_ready_with_too_few_patients(make_records):
    records = make_records([
        RecordSpec("only", "P-1 M 01-JAN-1970 A"),
        RecordSpec("only2", "P-1 M 01-JAN-1970 A"),  # same patient
    ])
    report = analyze_patients(records)
    assert report.n_patients == 1
    assert report.split_ready is False
    assert any(f.code == "INSUFFICIENT_PATIENTS_FOR_SPLIT" for f in report.findings)


def test_missing_identity_flagged(make_records):
    records = make_records([
        RecordSpec("anon", "X"),  # EDF+ anonymous patient field
        RecordSpec("b", "P-2 F 01-JAN-1980 B"),
        RecordSpec("c", "P-3 M 01-JAN-1990 C"),
    ])
    report = analyze_patients(records)
    assert any(f.code == "MISSING_PATIENT_IDENTITY" for f in report.findings)
