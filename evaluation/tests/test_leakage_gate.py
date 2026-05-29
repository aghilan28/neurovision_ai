"""Tests for the patient-disjoint validation gate."""

from __future__ import annotations

import pytest

from evaluation.splits import patient_disjoint_split
from evaluation.splits.schemas import Partition, SplitResult, SplitSpec
from evaluation.validation import (
    LeakageError,
    approve_split,
    detect_leakage,
    require_leakage_free,
    validate_split,
)


def _leaky_split():
    return SplitResult(
        spec=SplitSpec(scheme="patient_disjoint", base_seed=0, fractions={"train": 0.5, "test": 0.5}),
        partitions=(
            Partition("train", ("pX", "pY"), ("pX-r0", "pY-r0")),
            Partition("test", ("pX",), ("pX-r0",)),  # pX leaks into test
        ),
        population_fingerprint="fp",
        n_patients=2,
        n_records=2,
    )


@pytest.mark.leakage
def test_clean_split_is_leakage_free(population):
    split = patient_disjoint_split(population, base_seed=1)
    report = detect_leakage(split)
    assert report.leakage_free
    assert approve_split(split).approved


@pytest.mark.leakage
def test_patient_overlap_detected():
    report = detect_leakage(_leaky_split())
    assert not report.leakage_free
    assert "pX" in report.overlapping_patients
    assert "pX-r0" in report.overlapping_records
    assert any(f.code == "PATIENT_OVERLAP" for f in report.findings)


@pytest.mark.leakage
def test_leaky_split_not_approved():
    approval = approve_split(_leaky_split())
    assert not approval.approved
    assert "leakage" in approval.reason.lower()
    assert approval.blocking_findings


@pytest.mark.leakage
def test_require_leakage_free_raises():
    with pytest.raises(LeakageError):
        require_leakage_free(_leaky_split())


def test_validate_split_reports_structure(population):
    report = validate_split(patient_disjoint_split(population, base_seed=1))
    assert report.valid
    assert set(report.partition_summary) == {"train", "val", "test"}
