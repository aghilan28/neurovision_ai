"""Patient-disjoint split generation (AP-2 / NR-3).

This module owns the project's cardinal data invariant: **no patient appears in
more than one partition**. It produces a deterministic three-way patient-disjoint
split (train / calibration / test) and a LOSO iterator. The calibration partition
is itself patient-disjoint from train and test so that conformal prediction and
post-hoc calibration get an honest, leakage-free calibration set.

The split is *self-verifying*: ``assert_patient_disjoint`` raises if disjointness
is ever violated, and the orchestration code calls it before any training.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterator

import numpy as np

from .catalog import EEGDataset
from ._provenance import hash_obj


@dataclass(frozen=True)
class SplitConfig:
    """Pinned, hashable split parameters."""

    train_fraction: float = 0.5
    calibration_fraction: float = 0.25
    test_fraction: float = 0.25
    seed: int = 13

    def __post_init__(self) -> None:
        total = self.train_fraction + self.calibration_fraction + self.test_fraction
        if abs(total - 1.0) > 1e-9:
            raise ValueError("split fractions must sum to 1.0")
        if min(self.train_fraction, self.calibration_fraction, self.test_fraction) <= 0:
            raise ValueError("all split fractions must be positive")

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PatientDisjointSplit:
    """A verified patient-disjoint partition of a dataset by window index."""

    train_idx: np.ndarray
    calibration_idx: np.ndarray
    test_idx: np.ndarray
    train_patients: tuple
    calibration_patients: tuple
    test_patients: tuple
    dataset_version: str
    split_version: str
    config: dict

    def assert_patient_disjoint(self) -> None:
        """Raise ``AssertionError`` if any patient spans two partitions (NR-3)."""
        tr, ca, te = set(self.train_patients), set(self.calibration_patients), set(self.test_patients)
        if tr & ca:
            raise AssertionError(f"patient leakage train∩calibration: {sorted(tr & ca)}")
        if tr & te:
            raise AssertionError(f"patient leakage train∩test: {sorted(tr & te)}")
        if ca & te:
            raise AssertionError(f"patient leakage calibration∩test: {sorted(ca & te)}")
        for part in (self.train_idx, self.calibration_idx, self.test_idx):
            if part.size == 0:
                raise AssertionError("a partition is empty; patient-disjoint split is degenerate")

    def summary(self) -> dict:
        return {
            "split_version": self.split_version,
            "dataset_version": self.dataset_version,
            "n_train": int(self.train_idx.size),
            "n_calibration": int(self.calibration_idx.size),
            "n_test": int(self.test_idx.size),
            "train_patients": list(self.train_patients),
            "calibration_patients": list(self.calibration_patients),
            "test_patients": list(self.test_patients),
        }


def _indices_for_patients(dataset: EEGDataset, patients: set) -> np.ndarray:
    mask = np.isin(dataset.patient_ids, np.asarray(sorted(patients)))
    return np.nonzero(mask)[0].astype(int)


def patient_disjoint_split(
    dataset: EEGDataset, config: SplitConfig | None = None
) -> PatientDisjointSplit:
    """Produce a deterministic, verified three-way patient-disjoint split."""
    cfg = config or SplitConfig()
    patients = list(dataset.patients())
    if len(patients) < 3:
        raise ValueError("at least 3 patients required for a 3-way patient-disjoint split")

    # deterministic patient shuffle
    rng = np.random.default_rng(cfg.seed)
    order = np.array(patients)
    perm = rng.permutation(len(order))
    order = order[perm]

    n = len(order)
    n_train = max(1, int(round(cfg.train_fraction * n)))
    n_cal = max(1, int(round(cfg.calibration_fraction * n)))
    # guarantee at least one patient per partition
    n_train = min(n_train, n - 2)
    n_cal = min(n_cal, n - n_train - 1)
    train_p = set(order[:n_train].tolist())
    cal_p = set(order[n_train : n_train + n_cal].tolist())
    test_p = set(order[n_train + n_cal :].tolist())

    split = PatientDisjointSplit(
        train_idx=_indices_for_patients(dataset, train_p),
        calibration_idx=_indices_for_patients(dataset, cal_p),
        test_idx=_indices_for_patients(dataset, test_p),
        train_patients=tuple(sorted(train_p)),
        calibration_patients=tuple(sorted(cal_p)),
        test_patients=tuple(sorted(test_p)),
        dataset_version=dataset.dataset_version,
        split_version="",  # filled below
        config=cfg.as_dict(),
    )
    # split version binds dataset version + config + the resolved patient assignment
    split_version = "split@1.0.0+" + hash_obj(
        {
            "dataset_version": dataset.dataset_version,
            "config": cfg.as_dict(),
            "train_patients": list(split.train_patients),
            "calibration_patients": list(split.calibration_patients),
            "test_patients": list(split.test_patients),
        }
    )
    split = PatientDisjointSplit(
        train_idx=split.train_idx,
        calibration_idx=split.calibration_idx,
        test_idx=split.test_idx,
        train_patients=split.train_patients,
        calibration_patients=split.calibration_patients,
        test_patients=split.test_patients,
        dataset_version=dataset.dataset_version,
        split_version=split_version,
        config=cfg.as_dict(),
    )
    split.assert_patient_disjoint()
    return split


def loso_folds(dataset: EEGDataset) -> Iterator[tuple]:
    """Yield Leave-One-Subject-Out folds ``(held_out_patient, train_idx, test_idx)``.

    The canonical patient-disjoint regime (GLOSSARY → LOSO). Provided for
    completeness and for tests asserting disjointness across every fold.
    """
    for patient in dataset.patients():
        test_idx = _indices_for_patients(dataset, {patient})
        train_idx = np.nonzero(dataset.patient_ids != patient)[0].astype(int)
        yield patient, train_idx, test_idx
