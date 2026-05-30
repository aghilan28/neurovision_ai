"""Deterministic model evaluation engine (P4-G).

Evaluates a fitted model on a dataset split and produces a reproducible
``EvaluationRecord`` (accuracy / precision / recall / F1 / confusion matrix +
calibration + uncertainty + dataset metrics). Deterministic evaluation only.
"""

from __future__ import annotations

import numpy as np

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import EvaluationRecord, SplitName
from ..version import DETERMINISTIC_EPOCH
from . import metrics as M


def _resolve_split(bundle, preferred: SplitName) -> tuple[SplitName, np.ndarray]:
    order = {SplitName.TEST: ["test", "val", "train"],
             SplitName.VAL: ["val", "test", "train"],
             SplitName.TRAIN: ["train", "val", "test"]}[preferred]
    name_to_enum = {"train": SplitName.TRAIN, "val": SplitName.VAL, "test": SplitName.TEST}
    for name in order:
        idx = bundle.split_indices(name)
        if idx.size > 0:
            return name_to_enum[name], idx
    return preferred, np.array([], dtype=int)


def evaluate(model, bundle, *, training_run_id: str, n_classes: int,
             split: SplitName = SplitName.TEST,
             created_at: str = DETERMINISTIC_EPOCH) -> EvaluationRecord:
    """Evaluate ``model`` on the dataset's split; deterministic ``EvaluationRecord``."""
    used_split, idx = _resolve_split(bundle, split)
    X, y = bundle.X[idx], bundle.y[idx]
    probs = model.predict_proba(X) if idx.size else np.zeros((0, n_classes))
    y_pred = probs.argmax(axis=1) if idx.size else np.array([], dtype=int)

    cm = M.confusion_matrix(y, y_pred, n_classes)
    acc = M.accuracy(y, y_pred)
    macro_p, macro_r, macro_f1, per_class = M.precision_recall_f1(cm)
    calibration = M.calibration_metrics(y, probs)
    uncertainty = M.uncertainty_metrics(probs)
    classes, counts = (np.unique(y, return_counts=True) if y.size else (np.array([]), np.array([])))
    dataset_metrics = {
        "n_samples": int(idx.size), "n_classes": int(n_classes),
        "class_distribution": {str(int(c)): int(n) for c, n in zip(classes, counts)},
        "split_used": used_split.value,
    }
    metrics = {"accuracy": acc, "precision_macro": macro_p, "recall_macro": macro_r,
               "f1_macro": macro_f1}

    eval_key = hash_obj({
        "training_run_id": training_run_id, "split": used_split.value, "metrics": metrics,
        "confusion_matrix": cm.tolist(), "calibration": calibration, "uncertainty": uncertainty})
    identity = mint_identity("evaluation", {
        "training_run_id": training_run_id, "eval_key": eval_key})

    return EvaluationRecord(
        evaluation_id=identity.id, training_run_id=training_run_id, dataset_id=bundle.record.dataset_id,
        split=used_split, metrics=metrics,
        confusion_matrix=tuple(tuple(int(v) for v in row) for row in cm.tolist()),
        calibration=calibration, uncertainty=uncertainty, dataset_metrics=dataset_metrics,
        created_at=created_at)
