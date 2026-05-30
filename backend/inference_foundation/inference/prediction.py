"""Deterministic prediction engine (P5-D).

Turns validated class probabilities into a structured, reproducible ``PredictionRecord``
(predicted class, class probabilities, prediction scores, decision metadata). Pure
function of (model output, class labels) — no randomness.
"""

from __future__ import annotations

import numpy as np

from ..models.domain import PredictionClass, PredictionRecord, PredictionScore

_EPS = 1e-12


class PredictionError(RuntimeError):
    """Raised when an input cannot be assembled into the model's feature space."""


class PredictionEngine:
    """Builds a ``PredictionRecord`` from a model's class probabilities."""

    def assemble_input(self, input_feature_record, expected_feature_names: tuple[str, ...]) -> np.ndarray:
        """Assemble the input feature asset into the model's feature vector."""
        from backend.model_foundation.datasets import assemble_feature_vector

        names, row = assemble_feature_vector(input_feature_record)
        if tuple(names) != tuple(expected_feature_names):
            raise PredictionError("input feature names do not match the model's feature space")
        return row

    def build_prediction(self, probs: np.ndarray, *, class_labels: tuple[int, ...],
                         n_classes: int) -> PredictionRecord:
        probs = np.asarray(probs, dtype=np.float64)
        labels = [str(int(class_labels[i])) if i < len(class_labels) else str(i)
                  for i in range(n_classes)]
        pred_idx = int(np.argmax(probs))
        classes = tuple(PredictionClass(class_index=i, class_label=labels[i],
                                        probability=float(probs[i])) for i in range(n_classes))
        order = np.argsort(probs)[::-1]
        margin = float(probs[order[0]] - (probs[order[1]] if n_classes > 1 else 0.0))
        norm = np.log(n_classes) if n_classes > 1 else 1.0
        entropy = float(-np.sum(probs * np.log(probs + _EPS)) / (norm + _EPS))
        scores = (
            PredictionScore("max_probability", float(probs[pred_idx])),
            PredictionScore("margin", margin),
            PredictionScore("normalized_entropy", entropy),
        )
        decision_metadata = {
            "n_classes": n_classes, "argmax_index": pred_idx,
            "tie": bool(margin <= _EPS), "decision_rule": "argmax",
        }
        return PredictionRecord(
            predicted_class=pred_idx, predicted_label=labels[pred_idx], classes=classes,
            scores=scores, decision_metadata=decision_metadata)
