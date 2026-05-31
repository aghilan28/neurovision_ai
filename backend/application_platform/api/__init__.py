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


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    return authorization[7:] if authorization.lower().startswith("bearer ") else authorization


def create_app(service: ApplicationPlatformService) -> FastAPI:
    app = FastAPI(title="NeuroVision Application API",
                  version=APPLICATION_PLATFORM_VERSION,
                  description="Real EEG upload -> prediction -> report product API (Track 3).")

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
        return {"prepared": True, **svc._model_info}

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
    @app.post(f"/{API_V1}/uploads", status_code=201)
    def upload(body: UploadBody, authorization: Optional[str] = Header(default=None),
               svc: ApplicationPlatformService = Depends(hub)):
        token = _bearer(authorization)
        if not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        try:
            content = base64.b64decode(body.content_base64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"invalid base64: {exc}")
        # validate + store the upload only (analysis is a separate call)
        outcome = svc.upload_and_analyze(token=token, filename=body.filename, content=content)
        if not outcome.accepted:
            return JSONResponse(status_code=422, content={
                "accepted": False, "reason": outcome.reason, "upload": outcome.upload.to_dict()})
        return {"accepted": True, "upload": outcome.upload.to_dict(),
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

    return app


__all__ = ["create_app", "RegisterBody", "LoginBody", "UploadBody", "AnalyzeBody"]
