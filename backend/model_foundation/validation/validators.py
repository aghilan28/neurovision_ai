"""Model content validation (P4-K, build-time).

Validates the *content* of the dataset / training run / evaluation / model records and
determinism, producing structured ``(name, passed, detail)`` results that the service
persists in the immutable ``ModelValidationRecord``. Pure functions; no exceptions.
"""

from __future__ import annotations

import numpy as np

from ..models.domain import ModelArchitecture


class ModelContentValidator:
    """Build-time validation of the model-foundation records."""

    def dataset_integrity(self, dataset_record, bundle) -> tuple[str, bool, dict]:
        ok = (dataset_record.n_samples == int(bundle.X.shape[0])
              and dataset_record.n_features == int(bundle.X.shape[1])
              and bundle.y.shape[0] == bundle.X.shape[0]
              and (dataset_record.split is None or dataset_record.split.patient_disjoint)
              and len(dataset_record.feature_names) == dataset_record.n_features)
        return ("dataset_integrity", bool(ok),
                {"n_samples": dataset_record.n_samples, "n_features": dataset_record.n_features,
                 "patient_disjoint": (dataset_record.split.patient_disjoint
                                      if dataset_record.split else None)})

    def training_integrity(self, training_run) -> tuple[str, bool, dict]:
        m = training_run.training_metrics
        ok = (bool(training_run.params_fingerprint) and training_run.n_params > 0
              and 0.0 <= float(m.get("train_accuracy", -1)) <= 1.0
              and len(training_run.training_history) > 0 and training_run.seed is not None)
        return ("training_integrity", bool(ok),
                {"n_params": training_run.n_params, "train_accuracy": m.get("train_accuracy")})

    def evaluation_integrity(self, evaluation, n_classes) -> tuple[str, bool, dict]:
        cm = evaluation.confusion_matrix
        shape_ok = len(cm) == n_classes and all(len(r) == n_classes for r in cm)
        acc = float(evaluation.metrics.get("accuracy", -1))
        ok = shape_ok and (0.0 <= acc <= 1.0) and evaluation.dataset_metrics.get("n_samples", -1) >= 0
        return ("evaluation_integrity", bool(ok),
                {"accuracy": acc, "confusion_shape": [len(cm), len(cm[0]) if cm else 0]})

    def model_integrity(self, model_metadata, training_run) -> tuple[str, bool, dict]:
        ok = (model_metadata.architecture in set(ModelArchitecture)
              and model_metadata.n_params == training_run.n_params
              and model_metadata.n_features > 0 and model_metadata.n_classes >= 1
              and 0.0 <= model_metadata.train_accuracy <= 1.0)
        return ("model_integrity", bool(ok),
                {"architecture": model_metadata.architecture.value, "n_params": model_metadata.n_params})

    def determinism_integrity(self, determinism_ok, detail) -> tuple[str, bool, dict]:
        return ("determinism_integrity", bool(determinism_ok), dict(detail))

    def content_checks(self, *, dataset_record, bundle, training_run, evaluation, model_metadata,
                       n_classes, determinism_ok, determinism_detail) -> list[tuple]:
        return [
            self.dataset_integrity(dataset_record, bundle),
            self.training_integrity(training_run),
            self.evaluation_integrity(evaluation, n_classes),
            self.model_integrity(model_metadata, training_run),
            self.determinism_integrity(determinism_ok, determinism_detail),
        ]


def recompute_data_fingerprint(X: np.ndarray, y: np.ndarray, feature_names, sample_ids,
                               decimals: int) -> str:
    from ml.provenance import hash_array, hash_obj
    return hash_obj({
        "X": hash_array(np.round(X, decimals)), "y": [int(v) for v in y],
        "feature_names": list(feature_names), "sample_ids": list(sample_ids)})
