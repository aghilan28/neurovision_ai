"""``frontend/application_frontend/uploads`` — EEG upload UI controller (P7-E).

Drives the **actual** EEG upload workflow through the backend API: it validates the
selection client-side, sends the bytes, surfaces backend validation findings/status, and
keeps an upload-history view. It supports every P1 format the backend accepts (the
frontend imposes no format list of its own — it forwards bytes and renders the result).
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendUpload
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
        upload = FrontendUpload.from_body(resp["body"])
        self.state.add_upload(upload)
        return ActionResult(True, "upload", "success",
                            f"Uploaded {upload.filename} ({upload.size_bytes} bytes).",
                            data={"upload": upload.to_dict()})

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
