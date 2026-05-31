"""``backend/application_platform/api`` — real HTTP API layer (T3-C).

A real **FastAPI** application exposing the versioned (``/v1``) product endpoints:

    GET  /health                 - liveness + platform version
    GET  /v1/dataset/status      - Track-1 dataset status
    GET  /v1/model/status        - active model + Track-2 readiness
    POST /v1/auth/register        - register a user
    POST /v1/auth/login           - obtain a bearer token
    POST /v1/uploads              - upload a real EEG file (validate + bound)
    POST /v1/analyses             - run the analysis workflow for an upload
    GET  /v1/analyses/{id}/prediction - prediction + confidence + evidence
    GET  /v1/analyses/{id}/reports    - report set (+ ?format=json|html|pdf&type=...)
    GET  /v1/readiness            - application readiness

Typed Pydantic contracts, validation, version-aware, deterministic, documented (the
auto-generated OpenAPI schema). The API holds no business logic — it dispatches to the
``ApplicationPlatformService`` hub, which reuses ``application_backend`` + Tracks 1/2.

``create_app(service)`` builds the app around a hub instance, so a ``TestClient`` can drive
the real HTTP surface deterministically in tests + the verification script.
"""

from __future__ import annotations

import base64
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from ..service import ApplicationPlatformError, ApplicationPlatformService
from ..version import API_V1, APPLICATION_PLATFORM_VERSION
from backend.application_backend.models.domain import ApiOperation
from ..security import AuthenticationFailure, register_security_exception_handlers


# --- typed request contracts -------------------------------------------------
class RegisterBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=6)
    roles: Optional[list[str]] = None


class LoginBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UploadBody(BaseModel):
    filename: str = Field(min_length=1)
    content_base64: str = Field(min_length=1, description="base64-encoded EEG file bytes")


class AnalyzeBody(BaseModel):
    upload_id: str = Field(min_length=1)
    patient_key: Optional[str] = None
    case_key: Optional[str] = None


def create_app(service: ApplicationPlatformService) -> FastAPI:
    app = FastAPI(title="NeuroVision Application API",
                  version=APPLICATION_PLATFORM_VERSION,
                  description="Real EEG upload -> prediction -> report product API (Track 3).")

    # DBE-5: install controlled authentication-failure handlers so an invalid token / an
    # authorization denial renders a 401/403 (never a stack-trace-leaking HTTP 500).
    register_security_exception_handlers(app)

    def hub() -> ApplicationPlatformService:
        return service

    # --- health / status ----------------------------------------------------
    @app.get("/health")
    def health():
        return {"status": "ok", "service": "neurovision-application-api",
                "version": APPLICATION_PLATFORM_VERSION, "api_version": API_V1}

    @app.get(f"/{API_V1}/dataset/status")
    def dataset_status(svc: ApplicationPlatformService = Depends(hub)):
        return {"active_model": svc._model_info or None,
                "datasets": ["chb_mit"], "source": "track1:dataset_acquisition"}

    @app.get(f"/{API_V1}/model/status")
    def model_status(svc: ApplicationPlatformService = Depends(hub)):
        if not svc._model_info:
            return {"prepared": False}
        # MP-3: surface the model-recovery report (durability/identity-continuity) when present.
        rec = svc.model_recovery_report
        body = {"prepared": True, **svc._model_info}
        if rec is not None:
            body["recovery"] = rec.to_dict()
        return body

    # --- auth ----------------------------------------------------------------
    @app.post(f"/{API_V1}/auth/register", status_code=201)
    def register(body: RegisterBody, svc: ApplicationPlatformService = Depends(hub)):
        resp = svc.register(username=body.username, password=body.password, roles=body.roles)
        if not resp.ok:
            raise HTTPException(status_code=400, detail=resp.body)
        return resp.body

    @app.post(f"/{API_V1}/auth/login")
    def login(body: LoginBody, svc: ApplicationPlatformService = Depends(hub)):
        try:
            token = svc.login(username=body.username, password=body.password)
        except ApplicationPlatformError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        return {"token": token, "token_type": "bearer"}

    # --- upload + analyze ----------------------------------------------------
    @app.post(f"/{API_V1}/uploads")
    def upload(body: UploadBody, response: Response,
               authorization: Optional[str] = Header(default=None),
               svc: ApplicationPlatformService = Depends(hub)):
        # DBE-5: classify + validate the bearer credential BEFORE any work. Every invalid
        # token class (missing/empty/malformed/forged/expired/unknown) and every
        # authorization denial returns a controlled 401/403 here — the deep workflow is
        # only ever reached with a validated, authorized session, so an invalid token can
        # never reach business logic and can never produce an HTTP 500.
        auth_ctx = svc.authenticate_request(authorization, operation=ApiOperation.UPLOAD_EEG)
        if not auth_ctx.ok:
            raise AuthenticationFailure(auth_ctx)
        token = auth_ctx.token
        try:
            content = base64.b64decode(body.content_base64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"invalid base64: {exc}")
        # DBE-3: duplicate uploads must NEVER 500. The service classifies + short-circuits;
        # the endpoint maps the (deterministic) outcome to a deterministic status code.
        outcome = svc.upload_and_analyze(token=token, filename=body.filename, content=content)
        if not outcome.accepted:
            # a CONFLICTING_UPLOAD (same identity, different content) -> 409; else 422.
            code = 409 if outcome.duplicate_classification == "CONFLICTING_UPLOAD" else 422
            return JSONResponse(status_code=code, content={
                "accepted": False, "reason": outcome.reason or outcome.duplicate_classification,
                "duplicate_classification": outcome.duplicate_classification,
                "upload": outcome.upload.to_dict()})
        # New upload -> 201 Created; duplicate (reused existing result) -> 200 OK. Deterministic.
        response.status_code = 200 if outcome.is_duplicate else 201
        return {"accepted": True, "duplicate": outcome.is_duplicate,
                "duplicate_classification": outcome.duplicate_classification,
                "upload": outcome.upload.to_dict(),
                "analysis_id": outcome.analysis.analysis_id,
                "prediction": outcome.prediction_result.to_dict(),
                "readiness": outcome.readiness.to_dict()}

    @app.get(f"/{API_V1}/analyses/{{analysis_id}}/prediction")
    def get_prediction(analysis_id: str, svc: ApplicationPlatformService = Depends(hub)):
        try:
            outcome = svc.get_analysis(analysis_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"analysis {analysis_id} not found")
        return {"prediction": outcome.prediction_result.to_dict(),
                "evidence": outcome.prediction_result.evidence}

    @app.get(f"/{API_V1}/analyses/{{analysis_id}}/reports")
    def get_reports(analysis_id: str, type: str = "analysis", format: str = "json",
                    svc: ApplicationPlatformService = Depends(hub)):
        try:
            payloads = svc.reports_for(analysis_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"analysis {analysis_id} not found")
        if format == "json" and type == "all":
            return payloads
        key = f"{type}_report"
        if key not in payloads:
            raise HTTPException(status_code=400,
                                detail=f"unknown report type {type!r}; have "
                                       f"{sorted(k[:-7] for k in payloads)}")
        if format == "json":
            return payloads[key]
        from .. import reports as _reports
        rendered = _reports.export(payloads[key], format)
        if format == "html":
            return HTMLResponse(content=rendered)
        if format == "pdf":
            return Response(content=rendered, media_type="application/pdf")
        raise HTTPException(status_code=400, detail=f"unsupported format {format!r}")

    @app.get(f"/{API_V1}/readiness")
    def readiness(analysis_id: Optional[str] = None,
                  svc: ApplicationPlatformService = Depends(hub)):
        if analysis_id is None:
            ids = list(svc._analyses)
            if not ids:
                return {"classification": "NOT_READY", "reason": "no analyses yet"}
            analysis_id = ids[-1]
        outcome = svc.get_analysis(analysis_id)
        return outcome.readiness.to_dict()

    # --- DBE4-F: retrieval workflows (served from persisted/recovered state) ---
    @app.get(f"/{API_V1}/uploads/{{upload_id}}")
    def get_upload(upload_id: str, svc: ApplicationPlatformService = Depends(hub)):
        try:
            return svc.get_upload(upload_id).to_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail=f"upload {upload_id} not found")

    @app.get(f"/{API_V1}/analyses")
    def list_analyses(svc: ApplicationPlatformService = Depends(hub)):
        return {"analyses": svc.list_analyses(), "uploads": svc.list_uploads()}

    @app.get(f"/{API_V1}/analyses/{{analysis_id}}")
    def get_analysis(analysis_id: str, svc: ApplicationPlatformService = Depends(hub)):
        try:
            outcome = svc.get_analysis(analysis_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"analysis {analysis_id} not found")
        return outcome.to_dict()

    @app.get(f"/{API_V1}/persistence")
    def persistence_status(svc: ApplicationPlatformService = Depends(hub)):
        rep = svc.recovery_report
        mrec = svc.model_recovery_report
        return {"persistence_enabled": svc.persistence_enabled,
                "recovery": rep.to_dict() if rep else None,
                "model_recovery": mrec.to_dict() if mrec else None,
                "n_analyses": len(svc.list_analyses())}

    return app


__all__ = ["create_app", "RegisterBody", "LoginBody", "UploadBody", "AnalyzeBody"]
