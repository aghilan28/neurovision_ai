"""``backend/application_platform/predictions`` — prediction workflow projection (T3-F).

Projects the reused backend analysis into the product's prediction-request / prediction-result
records, bundling prediction + confidence + calibration + model information + readiness
information + evidence information — all traceable. No inference logic here (it is delegated
to the reused ``inference_foundation`` via ``application_backend``).
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import PredictionRequestRecord, PredictionResultRecord
from ..version import DETERMINISTIC_EPOCH


def build_prediction_request(*, upload_id: str, user_id: str, model_id: str, architecture: str,
                             created_at: str = DETERMINISTIC_EPOCH) -> PredictionRequestRecord:
    request_id = mint("app_prediction_request", {"upload_id": upload_id, "user_id": user_id,
                                                 "model_id": model_id})
    return PredictionRequestRecord(
        prediction_request_id=request_id, upload_id=upload_id, user_id=user_id, model_id=model_id,
        architecture=architecture, created_at=created_at)


def build_prediction_result(*, prediction_request_id: str, analysis, model_info: dict,
                            created_at: str = DETERMINISTIC_EPOCH) -> PredictionResultRecord:
    """Assemble the traceable prediction result + its evidence bundle."""
    conf = analysis.confidence_facet or {}
    confidence_score = float(conf.get("confidence_score", conf.get("score", 0.0)) or 0.0)
    evidence = {
        "confidence": {k: conf.get(k) for k in ("confidence_level", "confidence_score",
                                               "uncertainty", "interval")
                       if k in conf},
        "calibration": {k: analysis.calibration_facet.get(k)
                        for k in ("calibration_quality", "ece", "brier")
                        if k in (analysis.calibration_facet or {})},
        "explanation": {k: analysis.explanation_facet.get(k)
                        for k in ("method", "decision_factors", "top_features")
                        if k in (analysis.explanation_facet or {})},
        "model": model_info,
        "backend_prediction_id": analysis.prediction_id,
    }
    result_id = mint("app_prediction_result", {
        "prediction_request_id": prediction_request_id,
        "predicted_class": analysis.predicted_class,
        "predicted_label": analysis.predicted_label,
        "model_id": model_info.get("model_id")})
    return PredictionResultRecord(
        prediction_result_id=result_id, prediction_request_id=prediction_request_id,
        predicted_class=analysis.predicted_class, predicted_label=analysis.predicted_label,
        confidence_level=analysis.confidence_level, confidence_score=confidence_score,
        calibration_quality=analysis.calibration_quality, model_id=model_info.get("model_id", ""),
        model_architecture=model_info.get("architecture", ""),
        model_readiness=model_info.get("readiness", ""), evidence=evidence, created_at=created_at)


__all__ = ["build_prediction_request", "build_prediction_result"]
