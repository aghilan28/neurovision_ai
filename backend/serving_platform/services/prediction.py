"""Prediction service — response delivery (DRP3-D).

Projects the reused inference-foundation asset (prediction + confidence + calibration +
explanation) into a :class:`ServingResponseRecord` body for delivery. It **reuses** the
inference foundation's results and **duplicates no prediction logic** — it only selects and
shapes what is delivered (faithful uncertainty: confidence + calibration are always carried
alongside the label, NR-4).

The service that owns the execution id assigns the final ``response_id`` (via
``dataclasses.replace``) after this body is built.
"""

from __future__ import annotations

from ..models.domain import ResponseStatus, ServingResponseRecord
from ..version import DETERMINISTIC_EPOCH

# How many top explanation contributions to deliver.
EXPLANATION_TOP_K = 5


class PredictionService:
    """Builds a delivery response body from an inference asset; never recomputes predictions."""

    def build_response_body(self, request_record, inference_asset, *,
                            created_at: str = DETERMINISTIC_EPOCH) -> ServingResponseRecord:
        a = inference_asset
        # top-k explanation contributions by absolute importance (deterministic, name tiebreak)
        importance = a.explanation.feature_importance or a.explanation.feature_contributions
        ranked = sorted(importance, key=lambda c: (-abs(c.contribution), c.name))[:EXPLANATION_TOP_K]
        explanation_summary = tuple({"name": c.name, "contribution": round(float(c.contribution), 9)}
                                    for c in ranked)
        return ServingResponseRecord(
            response_id="",  # assigned by the service once the execution id is minted
            request_id=request_record.request_id, model_id=a.model_id, prediction_id=a.prediction_id,
            predicted_class=a.prediction.predicted_class,
            probability_scores=tuple(a.prediction.probabilities),
            confidence_level=a.confidence.confidence_level.value,
            confidence_score=a.confidence.confidence_score,
            calibration_quality=a.calibration.calibration_quality.value,
            expected_calibration_error=a.calibration.expected_calibration_error,
            explanation_summary=explanation_summary, status=ResponseStatus.DELIVERED, error=None,
            created_at=created_at)


__all__ = ["PredictionService", "EXPLANATION_TOP_K"]
