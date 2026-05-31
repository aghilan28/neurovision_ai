"""MP-1 — Model Provisioning Foundation tests.

Proves the deployment blocker is eliminated: a **fresh** NeuroVision deployment provisions a
usable model on startup, reaches ``/readyz ready:true``, and the upload -> analyze -> predict
workflow succeeds with **no** ``"no model prepared"`` exception and **no** HTTP 500 — with no
manual operator step. Also proves provisioning is deterministic + idempotent, the model is
registered with a valid audit chain, the model is available again after a restart, and
readiness is honest (true only when a model is actually available).

Uses the **real** production ASGI app (``server.app:app`` via ``build_application``), the real
``ApplicationPlatformService``, the real provisioning path, and the committed real EDF fixture
as a user upload — no mocks.
"""

from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

from fastapi.testclient import TestClient

from backend.application_platform import ApplicationPlatformService, provision_model
from backend.application_platform.provisioning import (
    ProvisioningReport, build_bootstrap_cohort, provision_model as provision_model_direct,
)
from backend.application_platform.server import build_application, load_config

from _track3_helpers import real_eeg_bytes

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _edf_b64() -> str:
    return base64.b64encode(real_eeg_bytes()).decode()


def _auth(client, username="op", roles=("clinician",)):
    client.post("/v1/auth/register",
                json={"username": username, "password": "pw-123456", "roles": list(roles)})
    return client.post("/v1/auth/login",
                       json={"username": username, "password": "pw-123456"}).json()["token"]


# =============================================================================
# MP1-C: the provisioning primitive (deterministic, idempotent, reuses prepare_model)
# =============================================================================
def test_provision_model_creates_usable_model():
    svc = ApplicationPlatformService()
    report = provision_model_direct(svc)
    assert isinstance(report, ProvisioningReport)
    assert report.ok and report.provisioned
    assert report.source == "bootstrap_cohort" and report.n_recordings == 2
    assert svc.backend.model_context is not None          # the inference context exists
    assert svc._model_info.get("model_id") == report.model_id


def test_provisioning_is_deterministic_across_instances():
    a = ApplicationPlatformService()
    ra = provision_model_direct(a)
    b = ApplicationPlatformService()
    rb = provision_model_direct(b)
    assert ra.model_id == rb.model_id  # same synthetic cohort + deterministic prepare_model


def test_provisioning_is_idempotent():
    svc = ApplicationPlatformService()
    r1 = provision_model_direct(svc)
    r2 = provision_model_direct(svc)         # second call: model already present -> no-op
    assert r2.already_present is True and r2.model_id == r1.model_id


def test_bootstrap_cohort_is_patient_disjoint(tmp_path):
    cohort = build_bootstrap_cohort(str(tmp_path), analysis_seconds=20.0)
    assert len(cohort) == 2
    patients = {p for p, _c, _f in cohort}
    assert len(patients) == 2                 # patient-disjoint (prepare_model requires >= 2)
    for _p, _c, path in cohort:
        assert os.path.exists(path)


# =============================================================================
# MP1-D/H: fresh production startup provisions + upload works (no 500)
# =============================================================================
def test_fresh_startup_provisions_and_ready():
    _svc, app = build_application(load_config({}))
    with TestClient(app) as c:                 # __enter__ runs the startup lifespan
        rz = c.get("/readyz").json()
        assert rz["ready"] is True and rz["model_prepared"] is True
        assert c.get("/v1/model/status").json()["prepared"] is True
        report = app.state.startup_report
        assert report.model_provisioned is True and report.model_id
        assert report.provisioning_source == "bootstrap_cohort"


def test_upload_after_fresh_startup_succeeds_no_500():
    _svc, app = build_application(load_config({}))
    with TestClient(app, raise_server_exceptions=False) as c:
        tok = _auth(c)
        r = c.post("/v1/uploads",
                   json={"filename": "valid_edf_plus.edf", "content_base64": _edf_b64()},
                   headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code in (200, 201)
        assert r.status_code != 500
        aid = r.json()["analysis_id"]
        assert c.get(f"/v1/analyses/{aid}/prediction").status_code == 200
        assert c.get(f"/v1/analyses/{aid}/reports").status_code == 200


def test_no_manual_preparation_required():
    # The ONLY action is starting the app (the lifespan). No prepare_model call in this test.
    _svc, app = build_application(load_config({}))
    with TestClient(app, raise_server_exceptions=False) as c:
        tok = _auth(c)
        r = c.post("/v1/uploads",
                   json={"filename": "v.edf", "content_base64": _edf_b64()},
                   headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code in (200, 201)


# =============================================================================
# MP1-E: readiness honesty (no false positive, no false negative)
# =============================================================================
def test_readiness_true_only_with_model():
    # provisioning ON -> ready true
    _svc, app = build_application(load_config({}))
    with TestClient(app) as c:
        assert c.get("/readyz").json()["ready"] is True


def test_readiness_false_without_model():
    # provisioning OFF -> ready MUST be false (honest; would 500 on upload otherwise)
    _svc, app = build_application(load_config({"provision_model": False}))
    with TestClient(app, raise_server_exceptions=False) as c:
        rz = c.get("/readyz").json()
        assert rz["ready"] is False and rz["model_prepared"] is False


def test_config_provision_flag_env(monkeypatch):
    monkeypatch.setenv("NV_PROVISION_MODEL", "0")
    assert load_config({}).provision_model is False
    monkeypatch.setenv("NV_PROVISION_MODEL", "1")
    assert load_config({}).provision_model is True
    monkeypatch.delenv("NV_PROVISION_MODEL", raising=False)
    assert load_config({}).provision_model is True  # default ON


# =============================================================================
# MP1-F: registry / audit / lineage integration
# =============================================================================
def test_provisioned_model_registered_with_lineage_and_audit():
    svc = ApplicationPlatformService()
    provision_model(svc)
    mr = svc.backend.model_context.model_record
    assert mr.model_id and getattr(mr, "lineage_id", None)     # registered with lineage
    assert svc.audit.verify() is True                          # audit chain intact
    assert "model_prepared" in [e.kind for e in svc.audit.events()]


# =============================================================================
# MP1-G: persistence / restart recovery (no manual steps, deterministic identity)
# =============================================================================
def test_model_available_after_restart(tmp_path):
    ws = str(tmp_path / "ws")
    cfg = load_config({"workspace_dir": ws})

    # boot 1: provision + upload (persists the analysis)
    svc1, app1 = build_application(cfg)
    with TestClient(app1, raise_server_exceptions=False) as c:
        assert c.get("/readyz").json()["ready"] is True
        tok = _auth(c)
        aid = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": _edf_b64()},
                     headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
        mid1 = svc1.backend.model_context.model_record.model_id

    # boot 2: restart on the SAME workspace -> model available again, no manual step
    svc2, app2 = build_application(cfg)
    with TestClient(app2, raise_server_exceptions=False) as c:
        rz = c.get("/readyz").json()
        assert rz["ready"] is True and rz["model_prepared"] is True
        assert svc2.audit.verify() is True
        mid2 = svc2.backend.model_context.model_record.model_id
        assert mid1 == mid2                                    # deterministic across restart
        # the previously-uploaded analysis recovered and is retrievable
        assert c.get(f"/v1/analyses/{aid}/reports").status_code == 200


# =============================================================================
# MP1-D (ASGI/Docker startup path): real uvicorn subprocess reaches ready:true
# =============================================================================
def _wait_ready(url, proc, tries=40):
    for _ in range(tries):
        if proc.poll() is not None:
            return None
        try:
            with urllib.request.urlopen(url + "/readyz", timeout=2) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1)
    return None


def test_real_uvicorn_startup_reaches_ready_with_model():
    port = 8771
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, NV_HOST="127.0.0.1", NV_PORT=str(port), NV_ENV="production")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",
         "backend.application_platform.server.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # poll until the server answers; once up, readiness must reflect a provisioned model
        ready = None
        for _ in range(40):
            ready = _wait_ready(url, proc, tries=1)
            if ready is not None:
                break
        assert ready is not None, "uvicorn server did not come up"
        assert ready["ready"] is True and ready["model_prepared"] is True
        # and a real upload over the live socket succeeds (no 500)
        reg = urllib.request.Request(
            url + "/v1/auth/register", method="POST",
            data=json.dumps({"username": "op", "password": "pw-123456",
                             "roles": ["clinician"]}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(reg, timeout=5)
        login = urllib.request.Request(
            url + "/v1/auth/login", method="POST",
            data=json.dumps({"username": "op", "password": "pw-123456"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(login, timeout=5) as r:
            tok = json.loads(r.read())["token"]
        up = urllib.request.Request(
            url + "/v1/uploads", method="POST",
            data=json.dumps({"filename": "v.edf", "content_base64": _edf_b64()}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(up, timeout=30) as r:
            assert r.status in (200, 201)
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
