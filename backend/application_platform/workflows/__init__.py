"""``backend/application_platform/workflows`` — analysis + prediction workflows (T3-E/F).

Orchestrates the product workflow by REUSING ``backend.application_backend`` (which already
runs the reused P1-P5 pipeline: upload -> validate -> process -> features -> select model ->
inference -> prediction + confidence + calibration + explanation). This module adds the
**bounded-segment** product step, the prediction-request/result projection, and the
prediction-evidence bundle (model + readiness + evidence). It duplicates no business logic.

Stages (T3-E): UPLOAD -> VALIDATE -> METADATA -> FEATURES -> SELECT_MODEL -> INFERENCE ->
RESULTS -> REPORT — every stage delegated to the reused services.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from backend.application_backend.api import ApiRequest
from backend.application_backend.models.domain import ApiOperation

from ..models.domain import WorkflowStage

ANALYSIS_STAGES = (WorkflowStage.UPLOAD, WorkflowStage.VALIDATE, WorkflowStage.METADATA,
                   WorkflowStage.FEATURES, WorkflowStage.SELECT_MODEL, WorkflowStage.INFERENCE,
                   WorkflowStage.RESULTS, WorkflowStage.REPORT)


@dataclass(frozen=True)
class BackendAnalysis:
    """The reused application_backend analysis outcome projected for Track 3."""

    backend_upload_id: str
    backend_analysis_id: str
    workflow_id: str
    prediction_id: str
    predicted_class: int
    predicted_label: str
    confidence_level: str
    calibration_quality: str
    prediction_facet: dict
    confidence_facet: dict
    calibration_facet: dict
    explanation_facet: dict
    reports: dict


class WorkflowError(RuntimeError):
    """Raised when the reused backend workflow rejects an analysis."""


def run_backend_analysis(backend, *, token: str, segment_path: str, filename: str,
                         patient_key: Optional[str] = None, case_key: Optional[str] = None,
                         created_at: str) -> BackendAnalysis:
    """Drive the reused application_backend upload -> analysis via its in-process API.

    ``backend`` is an ``ApplicationBackendService`` with a prepared model context. The
    bounded ``segment_path`` is the real (cropped) EEG analysed by the product.
    """
    api = backend.api
    with open(segment_path, "rb") as fh:
        content = fh.read()

    up = api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                               {"filename": os.path.basename(filename) or "upload.edf",
                                "content": content}, token=token), created_at=created_at)
    if not up.ok:
        raise WorkflowError(f"backend upload failed: {up.body}")
    backend_upload_id = up.body["upload_id"]

    an = api.handle(ApiRequest(ApiOperation.START_ANALYSIS,
                               {"upload_id": backend_upload_id, "patient_key": patient_key,
                                "case_key": case_key}, token=token), created_at=created_at)
    if not an.ok:
        raise WorkflowError(f"backend analysis failed: {an.body}")
    b = an.body
    analysis_id = b["analysis_id"]

    def facet(op):
        r = api.handle(ApiRequest(op, {"analysis_id": analysis_id}, token=token),
                       created_at=created_at)
        key = {ApiOperation.RETRIEVE_PREDICTION: "prediction",
               ApiOperation.RETRIEVE_CONFIDENCE: "confidence",
               ApiOperation.RETRIEVE_EXPLANATION: "explanation"}[op]
        return r.body.get(key, {}) if r.ok else {}

    prediction = facet(ApiOperation.RETRIEVE_PREDICTION)
    confidence = facet(ApiOperation.RETRIEVE_CONFIDENCE)
    explanation = facet(ApiOperation.RETRIEVE_EXPLANATION)
    calibration = backend.analysis_facet(analysis_id, "calibration")
    reports = api.handle(ApiRequest(ApiOperation.LIST_REPORTS, {"analysis_id": analysis_id},
                                    token=token), created_at=created_at).body.get("reports", {})

    return BackendAnalysis(
        backend_upload_id=backend_upload_id, backend_analysis_id=analysis_id,
        workflow_id=b["workflow_id"], prediction_id=b["prediction_id"],
        predicted_class=int(b.get("predicted_class", 0)),
        predicted_label=str(b.get("predicted_label", "")),
        confidence_level=str(b.get("confidence_level", "")),
        calibration_quality=str(b.get("calibration_quality", "")),
        prediction_facet=prediction, confidence_facet=confidence,
        calibration_facet=calibration, explanation_facet=explanation, reports=reports)


__all__ = ["ANALYSIS_STAGES", "BackendAnalysis", "WorkflowError", "run_backend_analysis"]
