"""``frontend/application_frontend/uploads`` — EEG upload UI controller (P7-E).

Drives the **actual** EEG upload workflow through the backend API: it validates the
selection client-side, sends the bytes, surfaces backend validation findings/status, and
keeps an upload-history view. It supports every P1 format the backend accepts (the
frontend imposes no format list of its own — it forwards bytes and renders the result).
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendUpload, FrontendWorkflow, FrontendPrediction
from ..forms import UPLOAD_FORM, validate_upload
from ..gateway import BackendGateway, OP_LIST_EEG, OP_UPLOAD_EEG, OP_RETRIEVE_EEG, is_success
from ..state import ApplicationState


class UploadController:
    def __init__(self, gateway: BackendGateway, state: ApplicationState):
        self.gateway = gateway
        self.state = state

    def upload(self, filename: str, content: bytes) -> ActionResult:
        errors = validate_upload(filename, content)
        if not errors.ok:
            return ActionResult(False, "upload", "error", "Please choose a valid EEG file.",
                                field_errors=errors.errors)
        resp = self.gateway.handle(OP_UPLOAD_EEG, {"filename": filename, "content": content},
                                   self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="upload")
        body = resp["body"]
        # The upload data is nested under "upload" key (from AnalysisOutcome.to_dict).
        upload_body = body.get("upload", body) if isinstance(body, dict) else body
        upload = FrontendUpload.from_body(upload_body)
        self.state.add_upload(upload)

        # The upload_and_analyze response includes the full pipeline results:
        # workflow, analysis, prediction_result, report, readiness.
        # Store them in frontend state so the Analysis, Prediction, and Reports
        # pages show data immediately after upload without needing a separate fetch.
        summary = {}
        wf_body = body.get("workflow") if isinstance(body, dict) else None
        if isinstance(wf_body, dict) and wf_body.get("analysis_id"):
            workflow = FrontendWorkflow(
                analysis_id=wf_body.get("analysis_id", ""),
                workflow_id=wf_body.get("workflow_id", ""),
                prediction_id=wf_body.get("prediction_result_id",
                               body.get("prediction_result", {}).get("prediction_result_id", "")),
                status=wf_body.get("status", "completed"),
                stages=tuple(wf_body.get("stages", ())),
            )
            self.state.add_workflow(workflow)
            summary["workflow"] = wf_body
            summary["analysis_id"] = wf_body.get("analysis_id")

        pred_body = body.get("prediction_result") if isinstance(body, dict) else None
        if isinstance(pred_body, dict) and summary.get("analysis_id"):
            # confidence and explanation must be dicts for build_prediction_view
            conf_score = pred_body.get("confidence_score")
            confidence_dict = (conf_score if isinstance(conf_score, dict)
                               else {"score": conf_score, "level": pred_body.get("confidence_level")})
            evidence = pred_body.get("evidence")
            explanation_dict = (evidence if isinstance(evidence, dict)
                                else {"summary": evidence} if evidence else {})
            prediction = FrontendPrediction(
                analysis_id=summary["analysis_id"],
                predicted_class=pred_body.get("predicted_class"),
                predicted_label=str(pred_body.get("predicted_label", "")),
                confidence_level=str(pred_body.get("confidence_level", "")),
                calibration_quality=str(pred_body.get("calibration_quality", "")),
                prediction=pred_body,
                confidence=confidence_dict,
                explanation=explanation_dict,
            )
            self.state.cache_prediction(prediction)
            summary["predicted_label"] = pred_body.get("predicted_label")
            summary["confidence_level"] = pred_body.get("confidence_level")

        return ActionResult(True, "upload", "success",
                            f"Uploaded {upload.filename} ({upload.size_bytes} bytes).",
                            data={"upload": upload.to_dict(), "summary": summary})

    def refresh_history(self) -> ActionResult:
        resp = self.gateway.handle(OP_LIST_EEG, {}, self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="upload")
        uploads = [FrontendUpload.from_body(b) for b in resp["body"].get("uploads", [])]
        self.state.set_uploads(uploads)
        return ActionResult(True, "upload", "info", f"{len(uploads)} upload(s).",
                            data={"count": len(uploads)})

    def retrieve(self, upload_id: str) -> ActionResult:
        resp = self.gateway.handle(OP_RETRIEVE_EEG, {"upload_id": upload_id}, self.state.token)
        if not is_success(resp):
            return from_api_error(resp, page="upload")
        return ActionResult(True, "upload", "info", "Upload retrieved.",
                            data={"upload": resp["body"].get("upload", {})})

    @staticmethod
    def upload_form() -> dict:
        return UPLOAD_FORM.to_dict()


__all__ = ["UploadController"]
