"""DBE-4 — Persistence wiring & state durability tests (backend/application_platform).

Proves application state survives a cold restart: upload + predict + report on one service
instance, construct a FRESH instance pointed at the same persistence root (a real restart),
and retrieve the upload / prediction / report / analysis / readiness from the recovered state —
with registry/audit/lineage references intact. Uses the real upload workflow over real EEG
fixtures + the real DRP-4 StorageEngine backend (no mocks). Also asserts the historical
ephemeral behaviour (no persistence root -> state not durable) so the wiring is explicit.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from _track3_helpers import make_product, real_eeg_bytes

from backend.application_platform import (
    ApplicationPlatformService, create_app,
)
from backend.model_foundation import ModelArchitecture
import os


def _prepare_persistent_product(tmp_path, *, analysis_seconds=2.0):
    """A real product whose state persists under tmp_path (model from real EDF fixtures)."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures", "eeg")
    svc = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                     analysis_seconds=analysis_seconds)
    cohort = [("p-a", "c-a", os.path.join(fixture_dir, "valid.edf")),
              ("p-b", "c-b", os.path.join(fixture_dir, "valid_edf_plus.edf"))]
    svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
    return svc


def _auth_upload(svc, content=None):
    c = TestClient(create_app(svc), raise_server_exceptions=False)
    c.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
    tok = c.post("/v1/auth/login", json={"username": "u", "password": "pw-123456"}).json()["token"]
    b64 = base64.b64encode(content or real_eeg_bytes()).decode()
    r = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
               headers={"Authorization": f"Bearer {tok}"})
    return c, r


# --- root cause: without persistence, state is NOT durable -------------------
def test_without_persistence_state_is_ephemeral():
    # the historical behaviour: no persistence root -> a fresh instance has no state
    svc1 = make_product(analysis_seconds=2.0)
    assert svc1.persistence_enabled is False
    _c, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    assert svc1.get_analysis(aid) is not None
    svc2 = make_product(analysis_seconds=2.0)  # "restart" without persistence
    import pytest
    with pytest.raises(KeyError):
        svc2.get_analysis(aid)  # lost, as the audit found


# --- the fix: state survives restart ----------------------------------------
def test_upload_prediction_report_survive_restart(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    assert svc1.persistence_enabled is True
    _c1, r = _auth_upload(svc1)
    body = r.json()
    aid = body["analysis_id"]
    upload_id = body["upload"]["upload_id"]
    pred_id = body["prediction"]["prediction_result_id"]

    # --- RESTART: a brand-new service at the same persistence root ---
    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    # recovery happened at construction
    rep = svc2.recovery_report
    assert rep is not None and rep.ok and rep.n_analyses == 1

    # upload survives
    assert svc2.get_upload(upload_id).upload_id == upload_id
    # prediction survives
    assert svc2.get_prediction(aid).prediction_result_id == pred_id
    # report survives
    assert svc2.get_report(aid).analysis_id == aid
    # analysis survives
    assert svc2.get_analysis(aid).analysis.analysis_id == aid
    # readiness survives
    assert svc2.get_readiness(aid).classification.value == "READY_FOR_USERS"


def test_retrieval_after_restart_via_api(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    upload_id = r.json()["upload"]["upload_id"]

    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    c2 = TestClient(create_app(svc2), raise_server_exceptions=False)
    # retrieval endpoints serve recovered state (no re-run of the workflow)
    assert c2.get(f"/v1/uploads/{upload_id}").status_code == 200
    assert c2.get(f"/v1/analyses/{aid}").status_code == 200
    assert c2.get(f"/v1/analyses/{aid}/prediction").status_code == 200
    assert c2.get(f"/v1/analyses/{aid}/reports", params={"type": "analysis"}).status_code == 200
    pj = c2.get("/v1/persistence").json()
    assert pj["persistence_enabled"] is True and pj["recovery"]["n_analyses"] == 1


def test_reports_exportable_after_restart(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    c2 = TestClient(create_app(svc2), raise_server_exceptions=False)
    # JSON / HTML / PDF all generate from recovered report payloads
    assert c2.get(f"/v1/analyses/{aid}/reports", params={"type": "analysis", "format": "json"}).status_code == 200
    assert c2.get(f"/v1/analyses/{aid}/reports", params={"type": "prediction", "format": "html"}).status_code == 200
    pdf = c2.get(f"/v1/analyses/{aid}/reports", params={"type": "evidence", "format": "pdf"})
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"


# --- registry / audit / lineage durability (DBE4-E) -------------------------
def test_registry_recovered_after_restart(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, _r = _auth_upload(svc1)
    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    counts = svc2.registry.counts()
    assert svc2.registry.orphans() == []
    assert counts["app_upload"] == 1 and counts["app_analysis"] == 1 and counts["app_report"] == 1


def test_lineage_references_survive_restart(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    out = svc2.get_analysis(aid)
    # the lineage references (ids) are intact on the recovered records
    assert out.report_record.lineage_id and out.prediction_result.lineage_id
    assert out.upload.lineage_id


# --- repeated restart (DBE4-G) ----------------------------------------------
def test_repeated_restart_is_stable(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    for _ in range(3):
        svc = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                         analysis_seconds=2.0)
        assert svc.recovery_report.ok and svc.recovery_report.n_analyses == 1
        assert svc.get_analysis(aid).analysis.analysis_id == aid
        assert svc.registry.orphans() == []


def test_determinism_recovered_ids_match(tmp_path):
    svc1 = _prepare_persistent_product(tmp_path)
    _c1, r = _auth_upload(svc1)
    aid = r.json()["analysis_id"]
    pred_id = r.json()["prediction"]["prediction_result_id"]
    svc2 = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                      analysis_seconds=2.0)
    out = svc2.get_analysis(aid)
    # recovered ids are identical to the originals (no reconstruction drift)
    assert out.analysis.analysis_id == aid
    assert out.prediction_result.prediction_result_id == pred_id


# --- empty store recovery (no prior state) ----------------------------------
def test_recovery_on_empty_store(tmp_path):
    svc = ApplicationPlatformService(persistence_root=str(tmp_path / "app_state"),
                                     analysis_seconds=2.0)
    assert svc.recovery_report.ok and svc.recovery_report.n_analyses == 0


# --- durable store unit-level -----------------------------------------------
def test_state_store_roundtrip(tmp_path):
    from backend.application_platform.persistence import ApplicationStateStore
    store = ApplicationStateStore(str(tmp_path / "s"))
    assert store.has_any() is False
    store.persist_analysis({"analysis_id": "app_analysis+abc", "outcome": {"x": 1}})
    assert store.has_any() is True
    assert store.analysis_ids() == ["app_analysis+abc"]
    assert store.load_payload("app_analysis+abc")["outcome"] == {"x": 1}
    # a fresh store at the same root sees the durable record (restart)
    store2 = ApplicationStateStore(str(tmp_path / "s"))
    assert store2.load_all_payloads()[0]["analysis_id"] == "app_analysis+abc"
