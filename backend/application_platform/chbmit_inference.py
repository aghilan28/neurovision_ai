"""``backend/application_platform/chbmit_inference.py`` — Inference engine for serialized CHB-MIT models.

Loads the serialized model config and weights from `data/chbmit_model.json` and reconstructs
the trained architecture (HybridModel or ReferenceArchitectureWrapper) to perform fast,
deterministic inference on windowed EEG features or raw segments.
"""

from __future__ import annotations

import os
import json
import numpy as np

from backend.production_models.architectures.models import HybridModel, ReferenceArchitectureWrapper
from backend.production_models.models.domain import ProductionArchitecture
from backend.real_model_training.data import _window_features


class CHBMitInferenceEngine:
    """Inference engine loaded from a serialized chbmit_model.json artifact."""

    def __init__(self, model_json_path: str):
        self.model_json_path = os.path.abspath(model_json_path)
        if not os.path.exists(self.model_json_path):
            raise FileNotFoundError(f"Model artifact not found at: {self.model_json_path}")
            
        with open(self.model_json_path, "r", encoding="utf-8") as fh:
            self.model_data = json.load(fh)
            
        self.architecture_summary = self.model_data["architecture_summary"]
        self.metrics = self.model_data["metrics"]
        self.payload = self.model_data["model_payload"]
        
        self.model = self._reconstruct_model(self.payload)

    def _reconstruct_model(self, payload: dict):
        """Reconstruct the model object from its serialized JSON parameters."""
        arch = ProductionArchitecture(payload["architecture"])
        seed = payload["seed"]
        n_classes = payload["n_classes"]
        hp = payload["hyperparameters"]
        
        if payload["type"] == "reference_wrapper":
            model = ReferenceArchitectureWrapper(arch, n_classes, seed=seed, hyperparameters=hp)
            # Load weights
            weights_np = {k: np.array(v) for k, v in payload["weights"].items()}
            model._inner.load_weights(weights_np)
            return model
        else:
            model = HybridModel(n_classes, seed=seed, hyperparameters=hp)
            # Load weights
            model._mean = np.array(payload["weights"]["mean"])
            model._std = np.array(payload["weights"]["std"])
            model._proj_a = np.array(payload["weights"]["proj_a"])
            model._proj_b = np.array(payload["weights"]["proj_b"])
            model._W = np.array(payload["weights"]["W"])
            model._b = np.array(payload["weights"]["b"])
            return model

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Run probability prediction on precomputed feature matrices (N, n_features)."""
        return self.model.predict_proba(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Run class prediction on precomputed feature matrices (N, n_features)."""
        return self.model.predict(X)

    def predict_raw_window(self, window: np.ndarray, sfreq: float) -> tuple[int, np.ndarray]:
        """Convert a raw window segment [channels, samples] to features and run inference.

        Returns `(predicted_class, class_probabilities)`.
        """
        # Ensure correct shape and float64 type
        window = np.asarray(window, dtype=np.float64)
        if window.ndim != 2:
            raise ValueError(f"Expected 2D array [channels, samples], got shape: {window.shape}")
            
        # Extract features
        features = _window_features(window, sfreq)
        features_batch = np.array([features])  # model expects a batch (1, n_features)
        
        # Predict
        proba = self.predict_proba(features_batch)[0]
        pred_class = int(np.argmax(proba))
        return pred_class, proba


__all__ = ["CHBMitInferenceEngine"]
