"""``frontend/application_frontend/predictions`` — prediction display (P7-G).

Retrieves and displays the **actual** prediction asset produced by the backend:
prediction, confidence, calibration summary, explanation summary, model information, and
analysis metadata. No mock data — every value comes from the backend prediction asset
via the API. Uncertainty (confidence + calibration) is always shown alongside the label
(NR-4).
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendPrediction
from ..gateway import (
    BackendGateway, OP_RETRIEVE_CONFIDENCE, OP_RETRIEVE_EXPLANATION, OP_RETRIEVE_PREDICTION,
    is_success,
)
from ..state import ApplicationState


class PredictionController:
    def __init__(self, gateway: BackendGateway, state: ApplicationState):
        self.gateway = gateway
        self.state = state

    def load(self, analysis_id: str) -> ActionResult:
        pred = self.gateway.handle(OP_RETRIEVE_PREDICTION, {"analysis_id": analysis_id},
                                   self.state.token)
        if not is_success(pred):
            return from_api_error(pred, page="prediction")
        conf = self.gateway.handle(OP_RETRIEVE_CONFIDENCE, {"analysis_id": analysis_id},
                                   self.state.token)
        expl = self.gateway.handle(OP_RETRIEVE_EXPLANATION, {"analysis_id": analysis_id},
                                   self.state.token)
        if not (is_success(conf) and is_success(expl)):
            return from_api_error(conf if not is_success(conf) else expl, page="prediction")

        prediction_body = pred["body"].get("prediction", {})
        confidence_body = conf["body"].get("confidence", {})
        explanation_body = expl["body"].get("explanation", {})
        prediction = FrontendPrediction(
            analysis_id=analysis_id,
            predicted_class=prediction_body.get("predicted_class"),
            predicted_label=str(prediction_body.get("predicted_label", "")),
            confidence_level=str(confidence_body.get("confidence_level", "")),
            calibration_quality=str(prediction_body.get("calibration_quality", "")
                                    or confidence_body.get("calibration_quality", "")),
            prediction=prediction_body, confidence=confidence_body, explanation=explanation_body)
        self.state.cache_prediction(prediction)
        return ActionResult(True, "prediction", "success", "Prediction loaded.",
                            data={"prediction": prediction.to_dict()})


def build_prediction_view(prediction: FrontendPrediction) -> dict:
    """A deterministic, presentation-ready view of a prediction asset."""
    classes = prediction.prediction.get("classes", [])
    top_factors = (prediction.explanation.get("decision_factors")
                   or prediction.explanation.get("feature_contributions") or [])[:5]
    return {
        "analysis_id": prediction.analysis_id,
        "predicted_label": prediction.predicted_label,
        "predicted_class": prediction.predicted_class,
        "confidence_level": prediction.confidence_level,
        "calibration_quality": prediction.calibration_quality,
        "class_probabilities": [
            {"class": c.get("class_index", c.get("class")), "label": c.get("label"),
             "probability": c.get("probability")} for c in classes],
        "confidence_score": prediction.confidence.get("score"),
        "explanation_method": prediction.explanation.get("method"),
        "top_factors": top_factors,
        "model_id": prediction.prediction.get("model_id"),
    }


__all__ = ["PredictionController", "build_prediction_view"]
