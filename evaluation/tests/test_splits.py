"""Tests for split generation (patient-disjoint by construction + deterministic)."""

from __future__ import annotations

import pytest

from evaluation.splits import leave_one_subject_out, patient_disjoint_split
from evaluation.splits.generator import SplitError
from evaluation.splits.population import patients_from_records


def _all_patients(split):
    out = []
    for p in split.partitions:
        out.extend(p.patient_ids)
    return out


def test_patient_disjoint_by_construction(multi_recording_population):
    split = patient_disjoint_split(multi_recording_population, base_seed=3)
    allp = _all_patients(split)
    assert len(allp) == len(set(allp))  # no patient in two partitions
    assert len(allp) == len(multi_recording_population)  # full coverage


def test_records_follow_patients(multi_recording_population):
    split = patient_disjoint_split(multi_recording_population, base_seed=3)
    # Every record of a partition's patients is in that partition, and nowhere else.
    seen_records = set()
    for part in split.partitions:
        expected = {r for pid in part.patient_ids for r in multi_recording_population[pid]}
        assert set(part.record_ids) == expected
        assert not (seen_records & set(part.record_ids))
        seen_records |= set(part.record_ids)


@pytest.mark.determinism
def test_split_deterministic_timestamp_independent(population):
    a = patient_disjoint_split(population, base_seed=7, created_at="t1")
    b = patient_disjoint_split(population, base_seed=7, created_at="t2")
    assert a.content_fingerprint == b.content_fingerprint
    assert a.split_id == b.split_id


def test_different_seed_changes_assignment(population):
    a = patient_disjoint_split(population, base_seed=1)
    b = patient_disjoint_split(population, base_seed=2)
    # Same population, different seed -> (very likely) different assignment, still valid.
    assert a.population_fingerprint == b.population_fingerprint
    a_all, b_all = _all_patients(a), _all_patients(b)
    assert len(set(a_all)) == len(set(b_all)) == len(population)


def test_three_patient_split_is_one_each():
    pop = {"a": ["a1"], "b": ["b1"], "c": ["c1"]}
    split = patient_disjoint_split(pop, base_seed=1)
    assert sorted(p.n_patients for p in split.partitions) == [1, 1, 1]


def test_too_few_patients_raises():
    with pytest.raises(SplitError):
        patient_disjoint_split({"a": ["a1"], "b": ["b1"]}, base_seed=1)  # 2 < 3 partitions


def test_invalid_fractions_raise(population):
    with pytest.raises(SplitError):
        patient_disjoint_split(population, fractions={"train": 0.6, "test": 0.6})
    with pytest.raises(SplitError):
        patient_disjoint_split(population, fractions={"train": 1.0, "test": 0.0})


def test_loso_folds(population):
    folds = leave_one_subject_out(population, base_seed=0)
    assert len(folds) == len(population)
    for fold in folds:
        test_part = fold.partition("test")
        train_part = fold.partition("train")
        assert test_part.n_patients == 1
        assert train_part.n_patients == len(population) - 1
        assert test_part.patient_ids[0] not in train_part.patient_ids


def test_patients_from_records_adapter():
    class R:
        def __init__(self, pid, fid):
            self.patient_id = pid
            self.file_id = fid

    records = [R("p1", "f1"), R("p1", "f2"), R("p2", "f3")]
    mapping = patients_from_records(records)
    assert mapping == {"p1": ["f1", "f2"], "p2": ["f3"]}
