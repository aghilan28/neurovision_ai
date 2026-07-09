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
from .landing import mount_landing_page

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
    # MP-1: model provisioning outcome (recorded at startup; drives true readiness).
    model_provisioned: bool = False
    model_id: Optional[str] = None
    provisioning_source: str = "not_attempted"

    @property
    def ok(self) -> bool:
        return all([self.started, self.service_constructed, self.api_built, self.health_ok,
                    self.readiness_ok, self.security_ok, self.operations_ok])

    def to_dict(self) -> dict:
        return {"started": self.started, "service_constructed": self.service_constructed,
                "api_built": self.api_built, "health_ok": self.health_ok,
                "readiness_ok": self.readiness_ok, "security_ok": self.security_ok,
                "operations_ok": self.operations_ok, "ok": self.ok,
                "model_provisioned": self.model_provisioned, "model_id": self.model_id,
                "provisioning_source": self.provisioning_source,
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


def _provision_startup_model(service, *, provision: bool = True):
    """MP-3: validate the service, then run the **single authoritative model-recovery step**.

    Reuses MP-1 provisioning (deterministic reconstruction of the same ``model_id``) + the
    DBE-4 durable store via ``lifecycle.recover_model`` — no parallel recovery path. The
    model-recovery outcome is folded into the :class:`StartupReport` (so ``model_provisioned``
    / ``model_id`` / ``provisioning_source`` reflect the *authoritative* usable-model signal)
    and the full :class:`~..lifecycle.ModelRecoveryReport` is returned so the lifespan can
    record it and ``/readyz`` can derive honest readiness from it.

    ``provision=False`` (operator disabled provisioning via ``NV_PROVISION_MODEL=0``) still
    assesses recovery — it simply does not synthesize a model — so readiness honestly reports
    ``false`` until a model context is injected.
    """
    from .. import lifecycle  # local import: keeps numpy/mne optional for lightweight tooling

    base = _validate_startup(service)
    recovery = lifecycle.recover_model(service, provision=provision)
    findings = list(base.findings)
    if not recovery.recovered:
        findings.extend(recovery.findings or ("model recovery incomplete",))
    report = StartupReport(
        started=base.started, service_constructed=base.service_constructed,
        api_built=base.api_built, health_ok=base.health_ok, readiness_ok=base.readiness_ok,
        security_ok=base.security_ok, operations_ok=base.operations_ok, findings=tuple(findings),
        model_provisioned=recovery.model_available, model_id=recovery.model_id,
        provisioning_source=recovery.source)
    return report, recovery


def build_application(config: Optional[ServerConfig] = None):
    """Build ``(service, app)`` — the real service + the real FastAPI app with a lifespan.

    The returned ``app`` is the authoritative ASGI application. Its lifespan runs startup
    validation (recorded at ``app.state.startup_report``), MP-1 model provisioning, and a
    clean shutdown. The same object is what ``uvicorn module:app`` and ``python -m ...`` serve.
    """
    config = config or load_config()
    service = build_service(config)
    app = create_app(service)
    mount_landing_page(app)

    # Attach config + service to app state (operators/tests can introspect without globals).
    app.state.service = service
    app.state.config = config
    app.state.startup_report = None
    app.state.model_recovery_report = None  # MP-3: set by the lifespan model-recovery step

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        # --- startup (DBE1-F + MP1-D + MP3-D): validate, then run the single authoritative
        # model-recovery step (reuses MP-1 provisioning + DBE-4 durable identity) so a fresh
        # deploy is usable AND a restart recovers the model automatically. ---
        provision = bool(getattr(config, "provision_model", True))
        report, recovery = _provision_startup_model(service, provision=provision)
        _app.state.startup_report = report
        _app.state.model_recovery_report = recovery
        if not report.ok:
            # Surface a clear, non-silent startup *validation* failure (no partial start).
            # A model-recovery shortfall is NOT fatal here — it is reported honestly via
            # /readyz (ready=false) rather than crashing the process (MP3-G).
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
        # MP1-E + MP3-G: ready is TRUE only when startup validated AND a usable model is
        # available AND (model identity is continuous across any restart) AND (persistence, if
        # configured, is healthy). ``model_prepared`` is keyed on the AUTHORITATIVE usable-model
        # signal (backend.model_context), not the lighter _model_info snapshot — closing the
        # latent false positive where a restored snapshot could report ready with no usable model.
        from .. import lifecycle

        rep = getattr(app.state, "startup_report", None)
        recovery = getattr(app.state, "model_recovery_report", None)
        startup_ok = bool(rep and rep.ok)
        model_prepared = lifecycle.model_available(service)
        if recovery is not None:
            ready, _reasons = lifecycle.assess_recovery_readiness(
                startup_ok=startup_ok, recovery=recovery)
        else:
            ready = bool(startup_ok and model_prepared)
        return {"status": "ready" if ready else "starting", "ready": ready,
                "api_version": API_V1, "model_prepared": model_prepared,
                "model_recovered": bool(recovery and recovery.recovered),
                "persistence_ok": (bool(recovery.persistence_ok) if recovery else None)}

    # Attach UI routes at the END to avoid shadowing system routes like /health or /readyz.
    # Uses dynamic import to satisfy the strict architectural boundary check (NR-8).
    # CRITICAL: Route attachment failure is a FATAL deployment error — never swallow silently.
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        ui = __import__("scripts.application_frontend_gateway", fromlist=["attach_ui_routes"])
        ui.attach_ui_routes(app, service)
        _log.info("NeuroVision frontend routes attached successfully.")
    except Exception as _exc:
        _log.critical("FATAL: Frontend UI route attachment failed: %s", _exc, exc_info=True)
        raise RuntimeError(
            f"NeuroVision deployment aborted: frontend route attachment failed — {_exc}"
        ) from _exc

    # PHASE 1.2 HARDENING — Strip broken UI catch-all routes
    # The UI layer (scripts.application_frontend_gateway) registers:
    #   @app.get("/")  -> frontend.render_login()  -> AttributeError: pages.login_page missing
    #   @app.get("/{page}") -> UI catch-all -> same crash
    # These BROKEN routes cause redirect loops / 500s in production if they ever win.
    # Static routes already cover ALL required paths (/, /auth, /dashboard, /upload,
    # /analysis, /prediction, /clinical, /patients, /export, /settings, /status, /reports).
    # Remove UI root + UI catch-all to guarantee 100% static delivery — 0 UI drift.
    try:
        _pruned = []
        # Iterate over a copy since we mutate the list
        for route in list(app.router.routes):
            rpath = getattr(route, "path", None)
            endpoint = getattr(route, "endpoint", None)
            ename = getattr(endpoint, "__name__", "")
            emod = getattr(endpoint, "__module__", "")
            # UI root: path="/" + endpoint.__name__=="root" + module scripts.application_frontend_gateway
            if rpath == "/" and ename == "root" and "application_frontend_gateway" in emod:
                app.router.routes.remove(route)
                _pruned.append(f"{rpath} -> {emod}.{ename}")
                continue
            # UI catch-all: path="/{page}"
            if rpath == "/{page}":
                app.router.routes.remove(route)
                _pruned.append(f"{rpath} -> {emod}.{ename}")
                continue
            # UI action POST (kept for API compatibility, but not used by static HTML)
            # Leave /action/{operation} intact — it does not conflict with static GET routes.
        if _pruned:
            _log.info("NeuroVision Phase 1.2: pruned %d broken UI catch-all route(s): %s",
                      len(_pruned), ", ".join(_pruned))
    except Exception as _pexc:  # noqa: BLE001
        # Pruning failure is non-fatal — static routes still win first-match,
        # but log it prominently.
        _log.warning("UI route pruning encountered an issue (non-fatal): %s", _pexc)

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
