"""Inference content validation (P5-K, build-time).

Validates the *content* of the prediction / confidence / calibration / explanation
records and determinism, producing structured ``(name, passed, detail)`` results that
the service persists in the immutable ``InferenceValidationRecord``. Pure functions; no
exceptions for bad content.
"""

from __future__ import annotations

import math

from ..models.domain import CalibrationQuality, ConfidenceLevel


class InferenceContentValidator:
    """Build-time validation of the inference records."""

    def prediction_integrity(self, prediction, n_classes: int) -> tuple[str, bool, dict]:
        probs = prediction.probabilities
        ok = (len(probs) == n_classes and all(math.isfinite(p) and 0.0 <= p <= 1.0 for p in probs)
              and abs(sum(probs) - 1.0) <= 1e-6 and 0 <= prediction.predicted_class < n_classes
              and prediction.classes[prediction.predicted_class].class_label == prediction.predicted_label)
        return ("prediction_integrity", bool(ok),
                {"n_classes": n_classes, "prob_sum": round(sum(probs), 6),
                 "predicted_class": prediction.predicted_class})

    def confidence_integrity(self, confidence) -> tuple[str, bool, dict]:
        lo, hi = confidence.confidence_interval
        ok = (0.0 <= confidence.confidence_score <= 1.0 and 0.0 <= lo <= hi <= 1.0
              and 0.0 <= confidence.prediction_stability <= 1.0
              and 0.0 <= confidence.prediction_reliability <= 1.0
              and confidence.confidence_level
              == ConfidenceLevel.from_score(confidence.prediction_reliability))
        return ("confidence_integrity", bool(ok),
                {"reliability": round(confidence.prediction_reliability, 6),
                 "level": confidence.confidence_level.value})

    def calibration_integrity(self, calibration) -> tuple[str, bool, dict]:
        ok = (0.0 <= calibration.expected_calibration_error <= 1.0
              and calibration.brier_score >= 0.0
              and 0.0 <= calibration.reliability_assessment <= 1.0
              and 0.0 <= calibration.confidence_consistency <= 1.0
              and calibration.calibration_quality
              == CalibrationQuality.from_ece(calibration.expected_calibration_error))
        return ("calibration_integrity", bool(ok),
                {"ece": round(calibration.expected_calibration_error, 6),
                 "quality": calibration.calibration_quality.value})

    def explanation_integrity(self, explanation, n_features: int) -> tuple[str, bool, dict]:
        n_contrib = len(explanation.feature_contributions)
        imp_sum = sum(c.contribution for c in explanation.feature_importance)
        ok = (n_contrib == n_features and len(explanation.feature_importance) == n_features
              and (abs(imp_sum - 1.0) <= 1e-6 or imp_sum == 0.0)
              and len(explanation.decision_factors) > 0)
        return ("explanation_integrity", bool(ok),
                {"n_contributions": n_contrib, "importance_sum": round(imp_sum, 6)})

    def determinism_integrity(self, determinism_ok, detail) -> tuple[str, bool, dict]:
        return ("determinism_integrity", bool(determinism_ok), dict(detail))

    def content_checks(self, *, prediction, confidence, calibration, explanation, n_classes,
                       n_features, determinism_ok, determinism_detail) -> list[tuple]:
        return [
            self.prediction_integrity(prediction, n_classes),
            self.confidence_integrity(confidence),
            self.calibration_integrity(calibration),
            self.explanation_integrity(explanation, n_features),
            self.determinism_integrity(determinism_ok, determinism_detail),
        ]
