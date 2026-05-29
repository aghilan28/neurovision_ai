"""Adapt patient-indexed datasets + deterministic preprocessing into batches.

``prepare_split`` applies the pinned preprocessing transform to a dataset and
slices it by a patient-disjoint split into train / calibration / test arrays,
returning a ``PreparedData`` bundle plus typed ``InputBatch`` contracts and the
exact preprocessing provenance used.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from preprocessing import transform, PreprocessingConfig, preprocessing_signature, PREPROCESSING_VERSION
from datasets import EEGDataset, PatientDisjointSplit

from ..schemas import InputBatch


@dataclass(frozen=True)
class PreparedData:
    """Model-ready, patient-disjoint arrays with provenance."""

    x_train: np.ndarray
    y_train: np.ndarray
    p_train: np.ndarray
    x_calibration: np.ndarray
    y_calibration: np.ndarray
    p_calibration: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    p_test: np.ndarray
    class_names: tuple[str, ...]
    preprocessing_version: str
    preprocessing_signature: str
    dataset_version: str
    split_version: str

    def train_batch(self) -> InputBatch:
        return InputBatch(self.x_train, self.p_train, self.preprocessing_version,
                          self.dataset_version, self.split_version)

    def calibration_batch(self) -> InputBatch:
        return InputBatch(self.x_calibration, self.p_calibration, self.preprocessing_version,
                          self.dataset_version, self.split_version)

    def test_batch(self) -> InputBatch:
        return InputBatch(self.x_test, self.p_test, self.preprocessing_version,
                          self.dataset_version, self.split_version)


def prepare_split(
    dataset: EEGDataset,
    split: PatientDisjointSplit,
    preprocessing_config: PreprocessingConfig | None = None,
) -> PreparedData:
    """Preprocess ``dataset`` and slice it by ``split`` into model-ready arrays."""
    if split.dataset_version != dataset.dataset_version:
        raise ValueError("split was generated for a different dataset version")
    cfg = preprocessing_config or PreprocessingConfig()
    x_all = transform(dataset.windows, cfg)  # deterministic

    def sl(idx: np.ndarray):
        return x_all[idx], dataset.labels[idx], dataset.patient_ids[idx]

    xtr, ytr, ptr = sl(split.train_idx)
    xca, yca, pca = sl(split.calibration_idx)
    xte, yte, pte = sl(split.test_idx)

    return PreparedData(
        x_train=xtr, y_train=ytr, p_train=ptr,
        x_calibration=xca, y_calibration=yca, p_calibration=pca,
        x_test=xte, y_test=yte, p_test=pte,
        class_names=dataset.class_names,
        preprocessing_version=PREPROCESSING_VERSION,
        preprocessing_signature=preprocessing_signature(cfg),
        dataset_version=dataset.dataset_version,
        split_version=split.split_version,
    )
