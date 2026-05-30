"""Deterministic calibration engine (P5-F).

Assesses probability calibration against a reference set (the model's dataset),
reusing the P4 calibration metrics (ECE + multiclass Brier). Produces a reliability
assessment, a confidence-consistency measure for the prediction, and a closed-vocabulary
calibration quality. Deterministic — no randomness.
"""

from __future__ import annotations

import numpy as np

from backend.model_foundation.evaluation import metrics as M  # intra-backend reuse

from ..models.domain import CalibrationQuality, CalibrationRecord

_EPS = 1e-12


class CalibrationEngine:
    """Deterministic probability-calibration assessment."""

    def assess(self, model, reference_X: np.ndarray, reference_y: np.ndarray, *,
               prediction_confidence: float, n_bins: int = 10) -> CalibrationRecord:
        ref_probs = (np.asarray(model.predict_proba(reference_X), dtype=np.float64)
                     if reference_X.shape[0] else np.zeros((0, 1)))
        cal = M.calibration_metrics(np.asarray(reference_y, dtype=int), ref_probs, n_bins=n_bins)
        ece = float(cal["ece"])
        brier = float(cal["brier"])
        reliability = float(np.clip(1.0 - ece, 0.0, 1.0))
        consistency = self._consistency(ref_probs, np.asarray(reference_y, dtype=int),
                                        prediction_confidence, n_bins)
        return CalibrationRecord(
            expected_calibration_error=ece, brier_score=brier, reliability_assessment=reliability,
            confidence_consistency=consistency, calibration_quality=CalibrationQuality.from_ece(ece),
            reference_n_samples=int(reference_X.shape[0]))

    def _consistency(self, ref_probs: np.ndarray, ref_y: np.ndarray, confidence: float,
                     n_bins: int) -> float:
        """How consistent the prediction's confidence is with the reference accuracy at
        that confidence bin (1.0 = perfectly consistent)."""
        if ref_probs.shape[0] == 0:
            return 1.0
        conf = ref_probs.max(axis=1)
        correct = (ref_probs.argmax(axis=1) == ref_y).astype(float)
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        b = min(int(confidence * n_bins), n_bins - 1)
        lo, hi = edges[b], edges[b + 1]
        mask = (conf > lo) & (conf <= hi) if b > 0 else (conf >= lo) & (conf <= hi)
        if not mask.any():
            return float(np.clip(1.0 - abs(confidence - float(correct.mean())), 0.0, 1.0))
        bin_acc = float(correct[mask].mean())
        return float(np.clip(1.0 - abs(confidence - bin_acc), 0.0, 1.0))
