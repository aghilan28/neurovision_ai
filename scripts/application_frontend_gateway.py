"""The frontend↔backend seam (Productization P7).

This is the **only** place that imports both the backend and the frontend. It adapts the
real ``backend.application_platform.ApplicationPlatformService`` to the frontend's abstract
:class:`BackendGateway` port, so the presentation layer can drive the *actual* backend
contracts without importing any domain module (NR-8). Scripts may import any layer; this
is the sanctioned composition point (like ``run_offline_inference`` /
``build_workstation_snapshot``).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from typing import Optional, Sequence

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.application_backend import ApplicationBackendService, ApiRequest, ApiOperation
from backend.model_foundation import ModelArchitecture
from frontend.application_frontend import BackendGateway, FrontendApp
from frontend.application_frontend.domain import FrontendUser, FrontendSession


class LiveBackendGateway(BackendGateway):
    """A concrete gateway that dispatches to a live ``ApplicationAPI`` instance."""

    def __init__(self, api):
        self.api = api
        self.call_log: list[str] = []

    def handle(self, operation: str, params: Optional[dict] = None,
               token: Optional[str] = None) -> dict:
        self.call_log.append(operation)
        response = self.api.handle(ApiRequest(ApiOperation(operation), params or {}, token=token))
        return response.to_dict()


class PlatformBackendGateway(BackendGateway):
    """A concrete gateway that dispatches to the ApplicationPlatformService."""

    def __init__(self, service):
        self.service = service

    def handle(self, operation: str, params: Optional[dict] = None,
               token: Optional[str] = None) -> dict:
        params = params or {}
        try:
            if operation == "register_user":
                resp = self.service.register(
                    username=params.get("username"),
                    password=params.get("password"),
                    roles=[params.get("role", "clinician")]
                )
                return resp.to_dict()

            if operation == "login":
                try:
                    login_result = self.service.login(
                        username=params.get("username"),
                        password=params.get("password")
                    )
                    # login() returns a namespace with .token and .session carrying
                    # real user_id and session_id from the backend.
                    if hasattr(login_result, "token"):
                        raw_token = login_result.token
                        user_id = (login_result.session.user_id
                                   if hasattr(login_result, "session") and login_result.session
                                   else "u-1")
                        session_id = (login_result.session.session_id
                                      if hasattr(login_result, "session") and login_result.session
                                      else "s-1")
                    else:
                        raw_token = login_result
                        user_id = "u-1"
                        session_id = "s-1"
                    return {"ok": True, "status": "ok", "body": {
                        "token": raw_token,
                        "user_id": user_id,
                        "session_id": session_id,
                        "username": params.get("username"),
                        "roles": ["clinician"]
                    }, "error_code": None}
                except Exception as exc:
                    return {"ok": False, "status": "unauthorized", "body": str(exc), "error_code": "AUTH_FAILED"}

            if operation == "logout":
                return {"ok": True, "status": "ok", "body": {}}

            if operation == "upload_eeg":
                if not token:
                    return {"ok": False, "status": "unauthorized",
                            "body": {"errors": [
                                {"check": "authentication",
                                 "detail": {"public": False, "session": None,
                                            "reason": "no_token_in_gateway"}},
                                {"check": "authorization",
                                 "detail": {"reason": "no_user"}}]},
                            "error_code": "authentication"}
                content = params.get("content")
                if isinstance(content, str):
                    content = base64.b64decode(content)
                # Lazy provisioning: if startup provisioning failed (e.g. OOM at boot),
                # retry now. Idempotent — skipped if model is already present.
                if not getattr(self.service, "_model_info", None) or \
                        getattr(self.service.backend, "model_context", None) is None:
                    from backend.application_platform.provisioning import provision_model
                    prov = provision_model(self.service)
                    if not prov.ok:
                        findings = "; ".join(prov.findings) if prov.findings else "unknown error"
                        return {"ok": False, "status": "error",
                                "body": {"error": f"Model not ready: {findings}"},
                                "error_code": "MODEL_NOT_READY"}
                outcome = self.service.upload_and_analyze(
                    token=token,
                    filename=params.get("filename"),
                    content=content
                )
                return {"ok": outcome.accepted, "status": "ok" if outcome.accepted else "error",
                        "body": outcome.to_dict()}

            if operation == "list_analysis_history":
                analyses = self.service.list_analyses()
                workflows = []
                for aid in analyses:
                    outcome = self.service.get_analysis(aid)
                    if outcome.workflow:
                        workflows.append(outcome.workflow.to_dict())
                return {"ok": True, "status": "ok", "body": {"analyses": workflows}}

            if operation == "list_eeg":
                uploads = self.service.list_uploads()
                records = [self.service.get_upload(uid).to_dict() for uid in uploads]
                return {"ok": True, "status": "ok", "body": {"uploads": records}}

            if operation == "retrieve_prediction":
                aid = params.get("analysis_id")
                outcome = self.service.get_analysis(aid)
                return {"ok": True, "status": "ok", "body": outcome.prediction_result.to_dict()}

            if operation == "list_reports":
                aid = params.get("analysis_id")
                if not aid: return {"ok": True, "status": "ok", "body": {"reports": []}}
                reports = self.service.reports_for(aid)
                report_list = []
                for name, content in reports.items():
                    report_list.append({"name": name, "content": content})
                return {"ok": True, "status": "ok", "body": {"reports": report_list}}

            if operation == "list_clinical_cases":
                return {"ok": True, "status": "ok", "body": {"cases": self.service.list_clinical_cases()}}
            if operation == "list_operational_events":
                return {"ok": True, "status": "ok", "body": {"events": self.service.list_operational_events()}}
            if operation == "list_autonomous_tasks":
                return {"ok": True, "status": "ok", "body": {"tasks": self.service.list_autonomous_tasks()}}
            if operation == "list_research_benchmarks":
                return {"ok": True, "status": "ok", "body": {"benchmarks": self.service.list_research_benchmarks()}}

            return {"ok": False, "status": "error", "body": f"Unhandled operation: {operation}"}
        except Exception as exc:
            return {"ok": False, "status": "error",
                    "body": {"error": str(exc)}, "error_code": "GATEWAY_ERROR"}


SECRET = b"neurovision-deployment-secret-key"


def _sign(data: str) -> str:
    return hmac.new(SECRET, data.encode(), hashlib.sha256).hexdigest()


def _get_frontend(request: Request, service) -> FrontendApp:
    gateway = PlatformBackendGateway(service)
    frontend = FrontendApp(gateway)
    raw_value = request.cookies.get("nv_session")
    if raw_value and "." in raw_value:
        try:
            encoded, sig = raw_value.rsplit(".", 1)
            if not hmac.compare_digest(_sign(encoded), sig):
                return frontend
            data = json.loads(base64.b64decode(encoded).decode("utf-8"))
            if data.get("user"):
                frontend.state.user = FrontendUser(**data["user"])
            if data.get("session"):
                frontend.state.session = FrontendSession(**data["session"])
            frontend.state._token = data.get("token")
            if data.get("current_page"):
                frontend.state.current_page = data["current_page"]
            for key in ("clinical_cases", "operational_events", "autonomous_tasks", "research_benchmarks"):
                if key in data:
                    setattr(frontend.state, key, data[key])
        except Exception:
            pass
    return frontend


def _set_session_cookie(response, frontend: FrontendApp):
    state = frontend.state
    data = {
        "user": state.user.__dict__ if state.user else None,
        "session": state.session.__dict__ if state.session else None,
        "token": state._token,
        "current_page": state.current_page,
    }
    for key in ("clinical_cases", "operational_events", "autonomous_tasks", "research_benchmarks"):
        val = getattr(state, key, None)
        if val is not None: data[key] = val
    encoded = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    value = f"{encoded}.{_sign(encoded)}"
    response.set_cookie(
        key="nv_session",
        value=value,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=86400,  # 24 hours
    )


def build_live_app(cohort_files: Sequence[tuple], *, workspace_dir: Optional[str] = None,
                   architecture: ModelArchitecture = ModelArchitecture.EEGNET,
                   dataset_key: str = "cohort", seed: int = 7, entropy=None):
    """Compose the real backend (with a prepared model) + a live gateway + a FrontendApp.

    Returns ``(service, gateway, app)``. The model is prepared via the backend's own
    ``prepare_model`` (a backend-admin step, not a UI action) so the frontend can then
    drive the user-facing flow end to end.
    """
    workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="nv_p7_")
    service = ApplicationBackendService(workspace_dir=workspace_dir, entropy=entropy)
    service.prepare_model(cohort_files, architecture=architecture, dataset_key=dataset_key,
                          seed=seed)
    gateway = LiveBackendGateway(service.api)
    app = FrontendApp(gateway)
    return service, gateway, app


def attach_ui_routes(app, service):
    """Attach the NeuroVision HTML frontend routes to the FastAPI app."""

    @app.get("/", response_class=HTMLResponse)
    def root(request: Request):
        frontend = _get_frontend(request, service)
        if frontend.is_authenticated:
            return RedirectResponse(url="/dashboard", status_code=303)
        return HTMLResponse(frontend.render_login())

    @app.get("/{page}", response_class=HTMLResponse)
    def ui_page(page: str, request: Request):
        frontend = _get_frontend(request, service)

        # UI page registry
        renderers = {
            "login": frontend.render_login,
            "register": frontend.render_register,
            "dashboard": frontend.dashboard,
            "upload": frontend.render_upload,
            "analysis": frontend.render_analysis,
            "prediction": frontend.render_prediction,
            "reports": frontend.render_reports,
            "clinical": frontend.render_clinical,
            "operations": frontend.render_operations,
            "autonomous": frontend.render_autonomous,
            "research": frontend.render_research,
        }

        if page == "logout":
            frontend.logout()
            response = RedirectResponse(url="/login", status_code=303)
            _set_session_cookie(response, frontend)
            return response

        if page not in renderers:
            # Fallthrough to other routes (e.g. /health, /v1) if not a UI page
            raise HTTPException(status_code=404)

        if page not in ("login", "register") and not frontend.is_authenticated:
            return RedirectResponse(url="/login", status_code=303)

        renderer = renderers.get(page)

        frontend.state.navigate(page)
        if page == "dashboard":
            frontend.dashboard()
            content = frontend.render_dashboard()
        elif page == "clinical":
            resp = frontend.gateway.handle("list_clinical_cases", {}, frontend.state.token)
            if resp.get("ok"): frontend.state.clinical_cases = resp["body"].get("cases", [])
            content = frontend.render_clinical()
        elif page == "operations":
            resp = frontend.gateway.handle("list_operational_events", {}, frontend.state.token)
            if resp.get("ok"): frontend.state.operational_events = resp["body"].get("events", [])
            content = frontend.render_operations()
        elif page == "autonomous":
            resp = frontend.gateway.handle("list_autonomous_tasks", {}, frontend.state.token)
            if resp.get("ok"): frontend.state.autonomous_tasks = resp["body"].get("tasks", [])
            content = frontend.render_autonomous()
        elif page == "research":
            resp = frontend.gateway.handle("list_research_benchmarks", {}, frontend.state.token)
            if resp.get("ok"): frontend.state.research_benchmarks = resp["body"].get("benchmarks", {})
            content = frontend.render_research()
        else:
            content = renderer()

        response = HTMLResponse(content)
        _set_session_cookie(response, frontend)
        return response

    @app.post("/action/{operation}")
    async def ui_action(operation: str, request: Request):
        frontend = _get_frontend(request, service)
        form_data = await request.form()
        params = dict(form_data)
        if operation in ("upload", "upload_eeg") and "file" in params:
            file = params["file"]
            if hasattr(file, "read"):
                content = await file.read()
                params["content"], params["filename"] = content, getattr(file, "filename", "upload.edf")

        result = None
        if operation == "login":
            result = frontend.login(params.get("username"), params.get("password"))
        elif operation in ("register", "register_user"):
            result = frontend.register(params.get("username"), params.get("password"),
                                     params.get("password_confirm"), params.get("role"))
        elif operation == "logout":
            result = frontend.logout()
        elif operation in ("upload", "upload_eeg"):
            result = frontend.upload(params.get("filename"), params.get("content"))
        elif operation == "start_analysis":
            result = frontend.start_analysis(params.get("upload_id"))

        if result and result.ok:
            response = RedirectResponse(url=f"/{result.page}", status_code=303)
        else:
            response = HTMLResponse(frontend.render_current())
        _set_session_cookie(response, frontend)
        return response


__all__ = ["LiveBackendGateway", "PlatformBackendGateway", "build_live_app", "attach_ui_routes"]
