"""Deterministic confidence engine (P5-E).

Assesses how confident/reliable a single prediction is: confidence score, a derived
confidence interval, perturbation-based prediction stability, a reliability blend, an
uncertainty summary, and a closed-vocabulary confidence level. Pure function of (model,
input, probabilities) — the perturbations are a fixed, deterministic set.
"""

from __future__ import annotations

import numpy as np

from ..models.domain import ConfidenceLevel, ConfidenceRecord

_EPS = 1e-12
_PERTURB_SCALES = (0.1, -0.1, 0.25, -0.25)
_MAX_PERTURB_FEATURES = 30


class ConfidenceEngine:
    """Deterministic per-prediction confidence assessment."""

    def assess(self, model, row: np.ndarray, probs: np.ndarray, *, n_classes: int) -> ConfidenceRecord:
        probs = np.asarray(probs, dtype=np.float64)
        pred_idx = int(np.argmax(probs))
        order = np.argsort(probs)[::-1]
        confidence = float(probs[pred_idx])
        second = float(probs[order[1]]) if n_classes > 1 else 0.0
        margin = float(confidence - second)
        norm = np.log(n_classes) if n_classes > 1 else 1.0
        entropy = float(-np.sum(probs * np.log(probs + _EPS)) / (norm + _EPS))

        stability = self._stability(model, row, pred_idx, n_classes)

        half_width = float(max(0.0, (1.0 - stability) * (1.0 - margin) * 0.5))
        ci = (float(max(0.0, confidence - half_width)), float(min(1.0, confidence + half_width)))

        reliability = float(np.clip(0.5 * confidence + 0.3 * stability + 0.2 * margin, 0.0, 1.0))
        uncertainty = {
            "normalized_entropy": entropy, "margin": margin, "second_probability": second,
            "top2_gap": margin,
        }
        return ConfidenceRecord(
            confidence_score=confidence, confidence_interval=ci, prediction_stability=stability,
            prediction_reliability=reliability, uncertainty_summary=uncertainty,
            confidence_level=ConfidenceLevel.from_score(reliability))

    def _stability(self, model, row: np.ndarray, pred_idx: int, n_classes: int) -> float:
        """Fraction of fixed deterministic perturbations that preserve the predicted class."""
        std = np.asarray(getattr(model, "_std", np.ones_like(row)), dtype=np.float64)
        std = np.where(std > _EPS, std, 1.0)
        n_feat = min(row.shape[0], _MAX_PERTURB_FEATURES)
        preserved = 0
        total = 0
        for i in range(n_feat):
            for scale in _PERTURB_SCALES:
                pert = row.copy()
                pert[i] = pert[i] + scale * std[i]
                p = np.asarray(model.predict_proba(pert.reshape(1, -1))[0], dtype=np.float64)
                preserved += int(np.argmax(p) == pred_idx)
                total += 1
        return float(preserved / total) if total else 1.0
