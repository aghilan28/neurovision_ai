"""Tests for the deterministic foundations: preprocessing + datasets + splits.

Covers determinism (AP-3/NR-9), reproducibility (AP-6/NR-10), and the cardinal
patient-disjoint invariant (AP-2/NR-3).
"""

from __future__ import annotations

import numpy as np

from preprocessing import transform, PreprocessingConfig, preprocessing_signature, PREPROCESSING_VERSION
from datasets import generate_dataset, SyntheticConfig, patient_disjoint_split, SplitConfig, loso_folds


def test_dataset_generation_is_deterministic(synthetic_config):
    a = generate_dataset(synthetic_config)
    b = generate_dataset(synthetic_config)
    assert np.array_equal(a.windows, b.windows)
    assert np.array_equal(a.labels, b.labels)
    assert a.dataset_version == b.dataset_version


def test_dataset_version_changes_with_config():
    a = generate_dataset(SyntheticConfig(n_patients=8, windows_per_patient=12, seed=1))
    b = generate_dataset(SyntheticConfig(n_patients=8, windows_per_patient=12, seed=2))
    assert a.dataset_version != b.dataset_version


def test_preprocessing_is_deterministic(dataset):
    cfg = PreprocessingConfig()
    x1 = transform(dataset.windows, cfg)
    x2 = transform(dataset.windows, cfg)
    assert np.array_equal(x1, x2)
    assert x1.dtype == np.float32
    assert x1.shape == dataset.windows.shape


def test_preprocessing_signature_binds_version_and_config():
    sig_a = preprocessing_signature(PreprocessingConfig())
    sig_b = preprocessing_signature(PreprocessingConfig(highpass_window=31))
    assert sig_a != sig_b
    assert PREPROCESSING_VERSION.startswith("preprocessing@")


def test_preprocessing_accepts_single_window(dataset):
    one = transform(dataset.windows[0], PreprocessingConfig())
    assert one.shape == dataset.windows[0].shape


def test_split_is_patient_disjoint(split):
    split.assert_patient_disjoint()
    tr, ca, te = set(split.train_patients), set(split.calibration_patients), set(split.test_patients)
    assert not (tr & ca) and not (tr & te) and not (ca & te)
    assert tr and ca and te  # all non-empty


def test_split_indices_map_to_correct_patients(dataset, split):
    for idx_set, patients in [
        (split.train_idx, split.train_patients),
        (split.calibration_idx, split.calibration_patients),
        (split.test_idx, split.test_patients),
    ]:
        got = set(int(p) for p in np.unique(dataset.patient_ids[idx_set]))
        assert got == set(patients)


def test_split_is_reproducible(dataset):
    a = patient_disjoint_split(dataset, SplitConfig())
    b = patient_disjoint_split(dataset, SplitConfig())
    assert a.split_version == b.split_version
    assert np.array_equal(a.test_idx, b.test_idx)


def test_loso_folds_are_patient_disjoint(dataset):
    n_folds = 0
    for held_out, train_idx, test_idx in loso_folds(dataset):
        train_p = set(int(p) for p in np.unique(dataset.patient_ids[train_idx]))
        test_p = set(int(p) for p in np.unique(dataset.patient_ids[test_idx]))
        assert test_p == {held_out}
        assert held_out not in train_p
        n_folds += 1
    assert n_folds == len(dataset.patients())
