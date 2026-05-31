"""``backend/application_platform/server/factory.py`` — application factory (DBE1-C).

The single authoritative construction path for a runnable NeuroVision HTTP service. It builds
the **real** Track-3 ``ApplicationPlatformService`` (which internally wires the reused
``application_backend`` → P1-P5 pipeline + model foundation + auth/security, over the shared
``ml.lineage`` tracker + the shared ``ImmutableAuditLog``) and the **real** Track-3 FastAPI app
via the existing ``create_app(service)`` — no mock services, no simplified paths, no business
logic. It additionally attaches an application **lifespan** (startup + shutdown) and a couple
of operational endpoints (``/livez``, ``/readyz``) that the ASGI entrypoint exposes.

This module does not modify datasets / models / inference / persistence / security /
operations / Track-1-4 — it only *constructs and serves* what already exists.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Optional

from .. import create_app
from ..service import ApplicationPlatformService
from ..version import APPLICATION_PLATFORM_VERSION, API_V1
from .config import ServerConfig, load_config


@dataclass
class StartupReport:
    """Deterministic record of what startup validated (no wall-clock)."""

    started: bool
    service_constructed: bool
    api_built: bool
    health_ok: bool
    readiness_ok: bool
    security_ok: bool
    operations_ok: bool
    findings: tuple = ()

    @property
    def ok(self) -> bool:
        return all([self.started, self.service_constructed, self.api_built, self.health_ok,
                    self.readiness_ok, self.security_ok, self.operations_ok])

    def to_dict(self) -> dict:
        return {"started": self.started, "service_constructed": self.service_constructed,
                "api_built": self.api_built, "health_ok": self.health_ok,
                "readiness_ok": self.readiness_ok, "security_ok": self.security_ok,
                "operations_ok": self.operations_ok, "ok": self.ok,
                "findings": list(self.findings)}


def build_service(config: Optional[ServerConfig] = None) -> ApplicationPlatformService:
    """Construct the real production application service from a validated config."""
    config = config or load_config()
    kwargs: dict = {}
    if config.workspace_dir:
        kwargs["workspace_dir"] = config.workspace_dir
    if config.analysis_seconds is not None:
        kwargs["analysis_seconds"] = config.analysis_seconds
    return ApplicationPlatformService(**kwargs)


def _validate_startup(service: ApplicationPlatformService) -> StartupReport:
    """Validate the constructed service can serve: health/readiness/security/operations.

    Read-only checks against the real systems — never trains a model, never mutates state.
    """
    findings: list[str] = []
    service_constructed = service is not None

    # security: the reused auth API is wired (a register/login dispatcher is reachable).
    security_ok = False
    try:
        security_ok = hasattr(service.backend, "api") and hasattr(service.backend.api, "handle")
        if not security_ok:
            findings.append("security: backend auth API not reachable")
    except Exception as exc:  # noqa: BLE001
        findings.append(f"security: {exc}")

    # operations: the Track-4 operations platform can observe this product (read-only).
    operations_ok = False
    try:
        from backend.operations_platform import OperationsPlatformService

        OperationsPlatformService(service)  # construct only; no qualification run at startup
        operations_ok = True
    except Exception as exc:  # noqa: BLE001
        findings.append(f"operations: {exc}")

    health_ok = bool(getattr(service, "version", None) == APPLICATION_PLATFORM_VERSION)
    if not health_ok:
        findings.append("health: service version mismatch")
    readiness_ok = hasattr(service, "registry") and hasattr(service, "audit")
    if not readiness_ok:
        findings.append("readiness: registry/audit not wired")

    return StartupReport(
        started=True, service_constructed=service_constructed, api_built=True,
        health_ok=health_ok, readiness_ok=readiness_ok, security_ok=security_ok,
        operations_ok=operations_ok, findings=tuple(findings))


def build_application(config: Optional[ServerConfig] = None):
    """Build ``(service, app)`` — the real service + the real FastAPI app with a lifespan.

    The returned ``app`` is the authoritative ASGI application. Its lifespan runs startup
    validation (recorded at ``app.state.startup_report``) and a clean shutdown. The same
    object is what ``uvicorn module:app`` and ``python -m ...`` both serve.
    """
    config = config or load_config()
    service = build_service(config)
    app = create_app(service)

    # Attach config + service to app state (operators/tests can introspect without globals).
    app.state.service = service
    app.state.config = config
    app.state.startup_report = None

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        # --- startup (DBE1-F) ---
        report = _validate_startup(service)
        _app.state.startup_report = report
        if not report.ok:
            # Surface a clear, non-silent startup failure.
            raise RuntimeError(f"NeuroVision startup validation failed: {report.findings}")
        try:
            yield
        finally:
            # --- shutdown (DBE1-G): clean, idempotent resource release ---
            _shutdown(service)

    # Install the lifespan on the existing app without rebuilding routes.
    app.router.lifespan_context = lifespan

    # --- operational probes (kube-style); reuse the existing /health semantics ---
    @app.get("/livez")
    def livez():
        return {"status": "alive", "version": APPLICATION_PLATFORM_VERSION}

    @app.get("/readyz")
    def readyz():
        rep = getattr(app.state, "startup_report", None)
        ready = bool(rep and rep.ok)
        return {"status": "ready" if ready else "starting", "ready": ready,
                "api_version": API_V1,
                "model_prepared": bool(getattr(service, "_model_info", None))}

    return service, app


def _shutdown(service: ApplicationPlatformService) -> dict:
    """Graceful, idempotent shutdown: release in-memory references; never raises (DBE1-G)."""
    report = {"shutdown": True, "cleaned": [], "errors": []}
    for attr in ("_analyses", "_uploads", "_reports"):
        try:
            store = getattr(service, attr, None)
            if isinstance(store, dict):
                store.clear()
                report["cleaned"].append(attr)
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"{attr}: {exc}")
    return report


__all__ = ["StartupReport", "build_service", "build_application", "_validate_startup", "_shutdown"]
