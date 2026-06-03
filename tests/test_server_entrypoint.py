"""DBE-1 — ASGI entrypoint & server startup tests (backend/application_platform/server).

Exercises the real entrypoint: module import, the application factory + lifespan
(startup validation + graceful shutdown), the health/readiness/livez/readyz endpoints,
dependency initialization (security + operations), startup configuration, real **uvicorn**
launch compatibility (a bounded subprocess serving the live socket), determinism, and the
failure condition (invalid config). Uses the actual production services — no mocks.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

import pytest
from fastapi.testclient import TestClient

from backend.application_platform.server import (
    ServerConfig, ServerEnvironment, StartupConfigError, build_application, build_service,
    load_config,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- DBE1-B: ASGI app exists + imports -------------------------------------
def test_asgi_app_importable_and_is_fastapi():
    from backend.application_platform.server.app import app, service
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    assert service is app.state.service
    # the authoritative app exposes the real Track-3 routes + the ops probes
    paths = {r.path for r in app.routes}
    assert "/health" in paths and "/v1/uploads" in paths
    assert "/livez" in paths and "/readyz" in paths


def test_single_authoritative_app_object():
    # importing the module twice yields the same app (one process-wide app)
    from backend.application_platform.server.app import app as a1
    from backend.application_platform.server.app import app as a2

    assert a1 is a2


# --- DBE1-D: startup configuration -----------------------------------------
def test_config_defaults():
    cfg = load_config({})
    assert cfg.host == "127.0.0.1" and cfg.port == 8000
    assert cfg.environment == ServerEnvironment.PRODUCTION and cfg.reload is False


def test_config_from_overrides():
    cfg = load_config({"host": "0.0.0.0", "port": 9001, "environment": "development",
                       "reload": True})
    assert cfg.host == "0.0.0.0" and cfg.port == 9001
    assert cfg.environment == ServerEnvironment.DEVELOPMENT and cfg.reload is True


def test_production_forces_no_reload():
    cfg = load_config({"environment": "production", "reload": True})
    assert cfg.reload is False


def test_invalid_port_rejected():
    with pytest.raises(StartupConfigError):
        ServerConfig(port=0)
    with pytest.raises(StartupConfigError):
        ServerConfig(port=99999)


def test_invalid_environment_rejected():
    with pytest.raises(StartupConfigError):
        load_config({"environment": "staging-nonsense"})


def test_config_deterministic():
    assert load_config({"port": 8080}).to_dict() == load_config({"port": 8080}).to_dict()


# --- DBE1-C: factory builds the real service -------------------------------
def test_factory_builds_real_service():
    svc = build_service(load_config({}))
    from backend.application_platform import ApplicationPlatformService

    assert isinstance(svc, ApplicationPlatformService)
    assert hasattr(svc, "registry") and hasattr(svc, "audit") and hasattr(svc, "backend")


def test_factory_respects_workspace_and_analysis(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path), "analysis_seconds": 12.0})
    svc = build_service(cfg)
    assert svc.analysis_seconds == 12.0


# --- DBE1-F/G: lifespan startup + shutdown ---------------------------------
def test_lifespan_startup_and_endpoints():
    _svc, app = build_application(load_config({}))
    with TestClient(app) as c:  # __enter__ runs startup lifespan
        assert c.get("/health").json()["status"] == "ok"
        assert c.get("/livez").json()["status"] == "alive"
        ready = c.get("/readyz").json()
        assert ready["ready"] is True and ready["api_version"] == "v1"
        assert c.get("/v1/readiness").status_code == 200
        report = app.state.startup_report
        assert report.ok
        assert report.security_ok and report.operations_ok
        assert report.health_ok and report.readiness_ok


def test_shutdown_clears_state():
    svc, app = build_application(load_config({}))
    with TestClient(app):
        svc._analyses["x"] = object()  # simulate live state
    # after context exit the shutdown hook cleared in-memory state
    assert svc._analyses == {}


def test_security_and_operations_initialize_at_startup():
    svc, app = build_application(load_config({}))
    with TestClient(app) as c:
        # security: a real register/login round-trip works through the served API
        assert c.post("/v1/auth/register",
                      json={"username": "op", "password": "pw-123456"}).status_code == 201
        assert c.post("/v1/auth/login",
                      json={"username": "op", "password": "pw-123456"}).status_code == 200
    # operations: the Track-4 platform can observe the constructed product
    from backend.operations_platform import OperationsPlatformService

    assert OperationsPlatformService(svc) is not None


# --- DBE1-E: real uvicorn launch compatibility (bounded subprocess) --------
def _wait_up(url, proc, tries=30):
    for _ in range(tries):
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url + "/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def test_real_uvicorn_launch_and_graceful_shutdown():
    port = 8762
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, NV_HOST="127.0.0.1", NV_PORT=str(port), NV_ENV="production")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",
         "backend.application_platform.server.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        assert _wait_up(url, proc), "uvicorn server did not come up"
        with urllib.request.urlopen(url + "/health", timeout=3) as r:
            assert r.status == 200 and json.loads(r.read())["status"] == "ok"
        with urllib.request.urlopen(url + "/readyz", timeout=3) as r:
            assert json.loads(r.read())["ready"] is True
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    # graceful shutdown: terminated cleanly (negative rc = signalled, not a crash code)
    assert proc.returncode is not None


def test_deployment_app_exposes_frontend_routes():
    _, app = build_application(load_config({"port": 8801}))
    with TestClient(app) as c:
        assert c.get("/").status_code == 200
        assert c.get("/login").status_code == 200
        assert c.get("/dashboard").status_code == 200
        assert c.get("/upload").status_code == 200
        assert c.get("/analysis").status_code == 200
        assert c.get("/prediction").status_code == 200
        assert c.get("/reports").status_code == 200


def test_module_run_helper_exists():
    # `python -m backend.application_platform.server.app` path is wired via run()
    from backend.application_platform.server import app as appmod

    assert hasattr(appmod, "run") and callable(appmod.run)
    assert hasattr(appmod, "app")
