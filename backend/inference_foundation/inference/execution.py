"""Deterministic model execution engine (P5-C).

Loads a trained model from a P4 ``ModelRecord`` by **deterministic reconstruction**
(reusing P4's ``build_feature_dataset`` + ``train`` on the original feature assets),
then **verifies** the reconstructed parameter fingerprint and training-run id match the
registered model. This is "model loading via reproducibility" — it reuses the P4
pipeline, never a parallel one, and the verification is the guarantee.

It also performs input/output validation around the actual numeric execution. There is
no serving and no API here — only deterministic, in-process model execution.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..version import INFERENCE_EXECUTION_VERSION


class ModelExecutionError(RuntimeError):
    """Raised when a model fails loading/verification or input/output validation."""


class ModelExecutionEngine:
    """Reconstructs + verifies a trained model and runs deterministic execution."""

    version = INFERENCE_EXECUTION_VERSION

    def load_model(self, model_record, train_feature_records, *, val_fraction: float = 0.2,
                   test_fraction: float = 0.2, dataset_key: str = "default"):
        """Reconstruct + verify the model. Returns (fitted_model, exec_metadata, bundle)."""
        from backend.model_foundation.datasets import build_feature_dataset
        from backend.model_foundation.training import train

        meta = model_record.metadata
        bundle = build_feature_dataset(
            train_feature_records, name=f"feature_dataset[{dataset_key}]", dataset_key=dataset_key,
            n_classes=meta.n_classes, val_fraction=val_fraction, test_fraction=test_fraction,
            seed=meta.seed)
        run, model = train(model_record.architecture, bundle, n_classes=meta.n_classes,
                           seed=meta.seed, hyperparameters=dict(meta.hyperparameters))

        params_verified = run.params_fingerprint == model_record.params_fingerprint
        version_verified = run.training_run_id == model_record.training_run_id
        if not params_verified:
            raise ModelExecutionError(
                "model verification failed: reconstructed parameter fingerprint does not match "
                f"the registered model ({run.params_fingerprint} != {model_record.params_fingerprint})")
        if not version_verified:
            raise ModelExecutionError(
                "model version verification failed: reconstructed training-run id does not match "
                f"({run.training_run_id} != {model_record.training_run_id})")

        exec_metadata = {
            "execution_version": self.version, "architecture": model_record.architecture.value,
            "model_id": model_record.model_id, "n_features": meta.n_features,
            "n_classes": meta.n_classes, "n_params": meta.n_params,
            "params_fingerprint_verified": True, "version_verified": True, "reconstructed": True,
        }
        return model, exec_metadata, bundle

    def validate_input(self, row: np.ndarray, expected_n_features: int) -> None:
        if row.ndim != 1 or row.shape[0] != expected_n_features:
            raise ModelExecutionError(
                f"input has {row.shape} features, expected ({expected_n_features},)")
        if not np.all(np.isfinite(row)):
            raise ModelExecutionError("input feature vector contains non-finite values")

    def execute(self, model, row: np.ndarray, *, n_classes: int) -> np.ndarray:
        """Run deterministic model execution; returns validated class probabilities."""
        probs = np.asarray(model.predict_proba(row.reshape(1, -1))[0], dtype=np.float64)
        self.validate_output(probs, n_classes)
        return probs

    def validate_output(self, probs: np.ndarray, n_classes: Optional[int] = None) -> None:
        if n_classes is not None and probs.shape[0] != n_classes:
            raise ModelExecutionError(f"output has {probs.shape[0]} classes, expected {n_classes}")
        if not np.all(np.isfinite(probs)):
            raise ModelExecutionError("output probabilities contain non-finite values")
        if abs(float(probs.sum()) - 1.0) > 1e-6:
            raise ModelExecutionError(f"output probabilities do not sum to 1 ({float(probs.sum())})")
