"""MP-3 — Persistent Model Lifecycle & Recovery tests.

Proves the model lifecycle is **durable**: a provisioned model survives restart, recovery is
automatic (no manual step), the model identity / registry / lineage / audit / readiness remain
valid across restarts, readiness stays honest (true only when a usable model is recoverable),
and failure conditions degrade in a controlled way (never a crash, never a silent false
positive).

Everything drives the **real** production ASGI app (``server.app:app`` via
``build_application``), the real ``ApplicationPlatformService``, the real MP-1 provisioning
path, and the real DBE-4 ``StorageEngine`` over a temp workspace — no mocks. The only
fault-injection is corrupting the real durable store (a genuine "persistence unavailable" /
"corruption" condition), which is unavoidable to exercise failure recovery.
"""

from __future__ import annotations

import base64
import shutil

from fastapi.testclient import TestClient

from backend.application_platform import (
    ApplicationPlatformService, assess_recovery_readiness, current_model_identity,
    model_available, recover_model,
)
from backend.application_platform.lifecycle import ModelRecoveryReport
from backend.application_platform.server import build_application, load_config

from _track3_helpers import real_eeg_bytes


def _edf_b64() -> str:
    return base64.b64encode(real_eeg_bytes()).decode()


def _auth(client, username="op"):
    client.post("/v1/auth/register",
                json={"username": username, "password": "pw-123456", "roles": ["clinician"]})
    return client.post("/v1/auth/login",
                       json={"username": username, "password": "pw-123456"}).json()["token"]


def _upload(client, token):
    return client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": _edf_b64()},
                       headers={"Authorization": f"Bearer {token}"})


# =============================================================================
# MP3-D: recover_model is the explicit, observable, idempotent recovery primitive
# =============================================================================
def test_recover_model_provisions_and_reports():
    svc = ApplicationPlatformService()                       # ephemeral (no persistence)
    rep = recover_model(svc)
    assert isinstance(rep, ModelRecoveryReport)
    assert rep.recovered is True and rep.model_available is True
    assert rep.source == "bootstrap_cohort" and rep.model_id
    assert rep.registered is True and rep.lineage_ok is True and rep.audit_ok is True
    assert svc.model_recovery_report is rep                  # stashed on the service


def test_recover_model_is_idempotent_and_deterministic():
    a = ApplicationPlatformService()
    b = ApplicationPlatformService()
    ra1 = recover_model(a)
    ra2 = recover_model(a)                                    # already present -> no-op source
    rb = recover_model(b)
    assert ra2.model_id == ra1.model_id == rb.model_id       # deterministic across instances
    assert ra2.source == "already_present"


# =============================================================================
# MP3-E: durable model identity + registry/lineage/metadata survive restart
# =============================================================================
def test_model_identity_persisted_durably(tmp_path):
    svc = ApplicationPlatformService(workspace_dir=str(tmp_path))
    rep = recover_model(svc)
    assert rep.identity_persisted is True
    stored = svc._state_store.load_model_identity()
    assert stored and stored["model_id"] == rep.model_id
    assert stored["architecture"] == "eegnet" and stored["lineage_id"]


def test_model_survives_restart_with_identity_continuity(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})

    svc1, app1 = build_application(cfg)
    with TestClient(app1, raise_server_exceptions=False):
        mid1 = svc1.backend.model_context.model_record.model_id
        rec1 = svc1.model_recovery_report
    assert rec1.recovered_from_persistence is False           # first boot: nothing prior

    svc2, app2 = build_application(cfg)
    with TestClient(app2, raise_server_exceptions=False):
        mid2 = svc2.backend.model_context.model_record.model_id
        rec2 = svc2.model_recovery_report
    assert mid1 == mid2                                        # identity survived the restart
    assert rec2.recovered_from_persistence is True
    assert rec2.identity_continuous is True and rec2.recovered is True
    assert rec2.registered is True and rec2.lineage_ok is True


def test_registry_lineage_audit_survive_restart(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})
    svc1, app1 = build_application(cfg)
    with TestClient(app1, raise_server_exceptions=False) as c:
        tok = _auth(c)
        aid = _upload(c, tok).json()["analysis_id"]

    svc2, app2 = build_application(cfg)
    with TestClient(app2, raise_server_exceptions=False) as c:
        # model lineage node re-created deterministically + verify_chain holds
        ident = current_model_identity(svc2)
        assert svc2.lineage.exists(ident["lineage_id"])
        assert svc2.lineage.verify_chain(ident["lineage_id"]) is True
        # audit chain intact after restart
        assert svc2.audit.verify() is True
        # the previously-uploaded analysis recovered + retrievable (registry consistent)
        assert c.get(f"/v1/analyses/{aid}/reports").status_code == 200
        assert svc2.recovery_report.ok is True


def test_repeated_restart_is_stable(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})
    ids = []
    for _ in range(3):
        svc, app = build_application(cfg)
        with TestClient(app, raise_server_exceptions=False) as c:
            assert c.get("/readyz").json()["ready"] is True
            ids.append(svc.backend.model_context.model_record.model_id)
            assert svc.model_recovery_report.identity_continuous is True
    assert len(set(ids)) == 1                                  # same identity every restart


# =============================================================================
# MP3-G: readiness honesty (no false positives / negatives) keyed on the authoritative signal
# =============================================================================
def test_readyz_true_only_with_recoverable_model(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})
    _svc, app = build_application(cfg)
    with TestClient(app) as c:
        rz = c.get("/readyz").json()
        assert rz["ready"] is True and rz["model_prepared"] is True
        assert rz["model_recovered"] is True and rz["persistence_ok"] is True


def test_readyz_false_when_provisioning_disabled():
    _svc, app = build_application(load_config({"provision_model": False}))
    with TestClient(app, raise_server_exceptions=False) as c:
        rz = c.get("/readyz").json()
        assert rz["ready"] is False and rz["model_prepared"] is False
        assert rz["model_recovered"] is False


def test_readiness_keys_on_authoritative_signal_not_snapshot(tmp_path):
    # A restored _model_info snapshot WITHOUT a usable inference context must NOT report ready
    # (the GAP-1 false positive). Simulate by restoring the snapshot but no context.
    svc = ApplicationPlatformService(workspace_dir=str(tmp_path))
    svc._model_info = {"model_id": "model+snapshotonly", "architecture": "eegnet"}
    assert model_available(svc) is False                       # no inference context
    rep = recover_model(svc, provision=False)                  # do not provision
    ready, reasons = assess_recovery_readiness(startup_ok=True, recovery=rep)
    assert ready is False and "model_unavailable" in reasons


# =============================================================================
# MP3-F: failure recovery — controlled behavior, no crashes, no silent corruption
# =============================================================================
def test_persistence_unavailable_makes_readiness_false(tmp_path):
    svc = ApplicationPlatformService(workspace_dir=str(tmp_path))
    recover_model(svc)                                         # healthy first
    # genuinely break the durable store: replace its root directory with a file (ENOTDIR)
    root = svc._state_store.root
    shutil.rmtree(root)
    open(root, "w").close()
    rep = recover_model(svc)                                   # must NOT raise
    ready, reasons = assess_recovery_readiness(startup_ok=True, recovery=rep)
    assert rep.persistence_ok is False and rep.recovered is False
    assert ready is False and "persistence_unavailable" in reasons
    # the model itself is still usable in-process (only durability is degraded)
    assert rep.model_available is True


def test_corrupt_model_identity_is_tolerated(tmp_path):
    svc = ApplicationPlatformService(workspace_dir=str(tmp_path))
    recover_model(svc)
    # corrupt the durable identity file with non-JSON bytes
    path = svc._state_store.engine._path("app.model", "provisioned")
    with open(path, "wb") as fh:
        fh.write(b"{ this is not valid json ")
    assert svc._state_store.load_model_identity() is None      # tolerated, not a crash
    # a fresh service still recovers a usable model + re-establishes the identity
    svc2 = ApplicationPlatformService(workspace_dir=str(tmp_path))
    rep2 = recover_model(svc2)
    assert rep2.recovered is True and rep2.identity_persisted is True


def test_identity_discontinuity_is_detected(tmp_path):
    svc = ApplicationPlatformService(workspace_dir=str(tmp_path))
    recover_model(svc)
    svc._state_store.persist_model_identity({
        "model_id": "model+DEADBEEFDEADBEEF", "architecture": "eegnet", "lineage_id": None,
        "dataset_key": "nv-bootstrap", "source": "bootstrap_cohort", "version": "x",
        "created_at": "1970-01-01T00:00:00Z"})
    svc2 = ApplicationPlatformService(workspace_dir=str(tmp_path))
    rep = recover_model(svc2)
    assert rep.identity_continuous is False and rep.recovered is False
    ready, reasons = assess_recovery_readiness(startup_ok=True, recovery=rep)
    assert ready is False and "model_identity_discontinuous" in reasons


def test_missing_persisted_state_is_fresh_not_a_crash(tmp_path):
    # No prior state at all -> recovery establishes a model with no prior identity, no error.
    cfg = load_config({"workspace_dir": str(tmp_path / "brand_new")})
    svc, app = build_application(cfg)
    with TestClient(app) as c:
        assert c.get("/readyz").json()["ready"] is True
    assert svc.model_recovery_report.recovered_from_persistence is False
    assert svc.model_recovery_report.recovered is True


# =============================================================================
# MP3-H: operator workflow — provision -> upload -> predict -> restart -> recover -> predict
# =============================================================================
def test_operator_workflow_survives_restart_no_manual_step(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})

    # boot 1: start -> (auto provision) -> upload -> predict -> report
    svc1, app1 = build_application(cfg)
    with TestClient(app1, raise_server_exceptions=False) as c:
        assert c.get("/readyz").json()["ready"] is True
        tok = _auth(c)
        r = _upload(c, tok)
        assert r.status_code in (200, 201) and r.status_code != 500
        aid = r.json()["analysis_id"]
        assert c.get(f"/v1/analyses/{aid}/prediction").status_code == 200
        mid1 = svc1.backend.model_context.model_record.model_id

    # boot 2: RESTART (same workspace) -> recover automatically -> upload + predict AGAIN
    svc2, app2 = build_application(cfg)
    with TestClient(app2, raise_server_exceptions=False) as c:
        assert c.get("/readyz").json()["ready"] is True        # recovered, no manual step
        assert c.get(f"/v1/analyses/{aid}/reports").status_code == 200   # prior result recovered
        tok = _auth(c, username="op2")
        r2 = c.post("/v1/uploads",
                    json={"filename": "v2.edf", "content_base64": _edf_b64()},
                    headers={"Authorization": f"Bearer {tok}"})
        assert r2.status_code in (200, 201) and r2.status_code != 500
        aid2 = r2.json()["analysis_id"]
        assert c.get(f"/v1/analyses/{aid2}/prediction").status_code == 200
        assert svc2.backend.model_context.model_record.model_id == mid1  # same model identity


def test_model_status_exposes_recovery(tmp_path):
    cfg = load_config({"workspace_dir": str(tmp_path)})
    _svc, app = build_application(cfg)
    with TestClient(app) as c:
        body = c.get("/v1/model/status").json()
        assert body["prepared"] is True
        assert body["recovery"]["recovered"] is True
        pers = c.get("/v1/persistence").json()
        assert pers["model_recovery"]["recovered"] is True
        assert pers["persistence_enabled"] is True
