"""Build a trainable dataset from registered feature assets (P4-C/D).

Assembles a fixed-length, channel-count-independent feature matrix ``X`` (and labels
``y``) from a collection of P3 ``FeatureRecord`` assets, plus a deterministic
patient-disjoint split. Returns a ``DatasetBundle`` (the in-memory arrays) and a
content-addressed ``DatasetRecord`` (the registry metadata). No raw EEG is touched —
only the already-validated feature vectors are read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np

from ml.provenance import content_id, hash_array, hash_obj  # allowed: backend -> ml

from ..models.domain import DatasetRecord, DatasetSource, DatasetStatus
from ..version import FINGERPRINT_DECIMALS
from .splits import patient_disjoint_split

# Fixed-length, channel-independent feature vectors used to assemble the model matrix.
ASSEMBLY_FEATURE_VECTORS: tuple[str, ...] = (
    "recording_temporal_summary", "synchronization", "spatial_summary",
    "topographic_stat", "band_summary", "regional_rms",
)


class DatasetBuildError(ValueError):
    """Raised when feature assets cannot be assembled into a consistent dataset."""


@dataclass(frozen=True)
class DatasetBundle:
    """The in-memory trainable dataset (arrays) + its registry record."""

    record: DatasetRecord
    X: np.ndarray
    y: np.ndarray
    sample_ids: tuple[str, ...]
    patient_ids: tuple[str, ...]
    feature_asset_ids: tuple[str, ...]

    def split_indices(self, split_name: str) -> np.ndarray:
        ids = {"train": self.record.split.train, "val": self.record.split.val,
               "test": self.record.split.test}[split_name]
        index = {sid: i for i, sid in enumerate(self.sample_ids)}
        return np.array([index[s] for s in ids if s in index], dtype=int)


def assemble_feature_vector(feature_record) -> tuple[tuple[str, ...], np.ndarray]:
    """Concatenate the fixed-length feature vectors of an asset into one row."""
    by_name = {v.name: v for v in feature_record.vectors}
    names: list[str] = []
    values: list[float] = []
    for vname in ASSEMBLY_FEATURE_VECTORS:
        v = by_name.get(vname)
        if v is None:
            raise DatasetBuildError(f"feature asset missing assembly vector {vname!r}")
        for label, value in zip(v.labels, v.values):
            names.append(f"{vname}.{label}")
            values.append(float(value))
    return tuple(names), np.asarray(values, dtype=np.float64)


def default_label_fn(feature_record, n_classes: int = 2) -> int:
    """A deterministic, content-derived label (for the model-creation framework/tests).

    This is NOT a clinical label — it is a reproducible labeling used to exercise
    training/evaluation. Real labels are supplied by the caller via ``labels``."""
    digest = hash_obj({"feature_asset_id": feature_record.feature_asset_id})
    return int(int(digest, 16) % n_classes)


def build_feature_dataset(feature_records: Sequence, *, name: str, dataset_key: str,
                          labels: Optional[dict] = None,
                          label_fn: Optional[Callable] = None, n_classes: int = 2,
                          val_fraction: float = 0.2, test_fraction: float = 0.2,
                          seed: int = 0) -> DatasetBundle:
    """Assemble a trainable ``DatasetBundle`` from feature assets."""
    from ..identity import mint_identity

    if not feature_records:
        raise DatasetBuildError("no feature assets supplied")

    feature_names: Optional[tuple[str, ...]] = None
    rows, ys, sample_ids, patient_ids, feature_asset_ids = [], [], [], [], []
    for rec in feature_records:
        names, row = assemble_feature_vector(rec)
        if feature_names is None:
            feature_names = names
        elif names != feature_names:
            raise DatasetBuildError("inconsistent feature names across assets")
        rows.append(row)
        if labels is not None:
            if rec.feature_asset_id not in labels:
                raise DatasetBuildError(f"no label for {rec.feature_asset_id}")
            ys.append(int(labels[rec.feature_asset_id]))
        else:
            ys.append((label_fn or default_label_fn)(rec, n_classes))
        sample_ids.append(rec.feature_asset_id)
        patient_ids.append(rec.patient_id)
        feature_asset_ids.append(rec.feature_asset_id)

    X = np.ascontiguousarray(np.vstack(rows), dtype=np.float64)
    y = np.asarray(ys, dtype=int)
    split = patient_disjoint_split(tuple(sample_ids), tuple(patient_ids),
                                   val_fraction=val_fraction, test_fraction=test_fraction, seed=seed)

    data_fp = hash_obj({
        "X": hash_array(np.round(X, FINGERPRINT_DECIMALS)), "y": [int(v) for v in y],
        "feature_names": list(feature_names), "sample_ids": list(sample_ids)})
    identity = mint_identity("dataset", {
        "source": DatasetSource.FEATURE_ASSETS.value, "dataset_key": dataset_key, "content_key": data_fp})
    classes, counts = np.unique(y, return_counts=True)
    class_distribution = {str(int(c)): int(n) for c, n in zip(classes, counts)}

    record = DatasetRecord(
        dataset_id=identity.id, source=DatasetSource.FEATURE_ASSETS, name=name, n_samples=int(X.shape[0]),
        n_features=int(X.shape[1]), feature_names=feature_names,
        class_labels=tuple(int(c) for c in classes), class_distribution=class_distribution,
        patient_ids=tuple(sorted(set(patient_ids))), feature_asset_ids=tuple(feature_asset_ids),
        split=split, data_fingerprint=data_fp, status=DatasetStatus.REGISTERED,
        source_metadata={"n_classes": int(len(classes)), "seed": seed})
    return DatasetBundle(record=record, X=X, y=y, sample_ids=tuple(sample_ids),
                         patient_ids=tuple(patient_ids), feature_asset_ids=tuple(feature_asset_ids))


def dataset_content_id(prefix: str, payload: dict) -> str:
    return content_id(prefix, payload)
