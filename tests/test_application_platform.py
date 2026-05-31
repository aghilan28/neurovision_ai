"""Track 3 — Real Product Application tests (backend/application_platform).

Exercises the real FastAPI API, the EEG upload workflow, the analysis + prediction
workflows, report generation (JSON/HTML/PDF), readiness, audit + lineage integration,
registry, determinism, and the boundary / corrupted-EEG / invalid-request / missing-model
conditions — driving the **real** HTTP surface (FastAPI ``TestClient``) over the committed
**real EDF fixtures** + a **real Track-2-style model** (no synthetic workflows, no network).
"""

from __future__ import annotations

import base64

import pytest

from _track3_helpers import make_client, make_product, real_eeg_bytes

from backend.application_platform import (
    ApplicationPlatformService, ApplicationReadinessClass, EntityKind, validate_entity,
)


def _auth(client):
    client.post("/v1/auth/register", json={"username": "alice", "password": "pw-123456",
                                           "roles": ["clinician"]})
    return client.post("/v1/auth/login",
                       json={"username": "alice", "password": "pw-123456"}).json()["token"]


# --- T3-C: API ---------------------------------------------------------------
def test_health_endpoint():
    client = make_client(make_product())
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.json()["api_version"] == "v1"


def test_status_endpoints_report_model_and_dataset():
    client = make_client(make_product())
    assert client.get("/v1/model/status").json()["prepared"] is True
    assert "chb_mit" in client.get("/v1/dataset/status").json()["datasets"]


def test_openapi_schema_is_documented():
    client = make_client(make_product())
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/health" in paths and "/v1/uploads" in paths
    assert "/v1/auth/login" in paths and "/v1/analyses/{analysis_id}/reports" in paths


def test_auth_register_and_login():
    client = make_client(make_product())
    assert client.post("/v1/auth/register",
                       json={"username": "bob", "password": "pw-123456"}).status_code == 201
    r = client.post("/v1/auth/login", json={"username": "bob", "password": "pw-123456"})
    assert r.status_code == 200 and r.json()["token"]


# --- T3-D: upload workflow ---------------------------------------------------
def test_upload_requires_auth():
    client = make_client(make_product())
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    r = client.post("/v1/uploads", json={"filename": "x.edf", "content_base64": b64})
    assert r.status_code == 401


def test_upload_rejects_corrupted_eeg():
    client = make_client(make_product())
    tok = _auth(client)
    bad = base64.b64encode(b"this is not an EEG file").decode()
    r = client.post("/v1/uploads", json={"filename": "bad.edf", "content_base64": bad},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
    assert r.json()["accepted"] is False


def test_upload_rejects_invalid_base64():
    client = make_client(make_product())
    tok = _auth(client)
    r = client.post("/v1/uploads", json={"filename": "x.edf", "content_base64": "!!!notb64!!!"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400


def test_invalid_request_body_is_422():
    client = make_client(make_product())
    tok = _auth(client)
    # missing required content_base64
    r = client.post("/v1/uploads", json={"filename": "x.edf"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422


# --- T3-E/F: analysis + prediction workflow ----------------------------------
def test_full_upload_to_prediction_workflow():
    client = make_client(make_product())
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    up = client.post("/v1/uploads", json={"filename": "valid_edf_plus.edf", "content_base64": b64},
                     headers={"Authorization": f"Bearer {tok}"})
    assert up.status_code == 201
    body = up.json()
    assert body["accepted"] is True
    pred = body["prediction"]
    assert pred["predicted_label"] != "" and pred["model_id"]
    aid = body["analysis_id"]
    pr = client.get(f"/v1/analyses/{aid}/prediction")
    assert pr.status_code == 200
    ev = pr.json()["evidence"]
    assert {"confidence", "calibration", "explanation", "model"} <= set(ev)


def test_missing_model_rejected():
    # a hub with no prepared model must refuse analysis (not crash)
    svc = ApplicationPlatformService()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    with pytest.raises(Exception):
        client.post("/v1/uploads", json={"filename": "x.edf", "content_base64": b64},
                    headers={"Authorization": f"Bearer {tok}"})


# --- T3-G: reports (JSON / HTML / PDF) ---------------------------------------
def test_reports_export_all_formats():
    client = make_client(make_product())
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    aid = client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                      headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
    rj = client.get(f"/v1/analyses/{aid}/reports", params={"type": "analysis", "format": "json"})
    assert rj.status_code == 200 and rj.json()["report_type"] == "analysis"
    rh = client.get(f"/v1/analyses/{aid}/reports", params={"type": "prediction", "format": "html"})
    assert rh.status_code == 200 and rh.headers["content-type"].startswith("text/html")
    assert b"<html" in rh.content.lower()
    rp = client.get(f"/v1/analyses/{aid}/reports", params={"type": "evidence", "format": "pdf"})
    assert rp.status_code == 200 and rp.content[:5] == b"%PDF-"


def test_report_types_present():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    aid = client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                      headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
    payloads = svc.reports_for(aid)
    for t in ("analysis", "prediction", "metadata", "model", "evidence", "audit", "lineage",
              "readiness"):
        assert f"{t}_report" in payloads


# --- T3-H: registry ----------------------------------------------------------
def test_registry_has_no_orphans():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                headers={"Authorization": f"Bearer {tok}"})
    counts = svc.registry.counts()
    assert svc.registry.orphans() == []
    for kind in (EntityKind.UPLOAD, EntityKind.PREDICTION_RESULT, EntityKind.ANALYSIS,
                 EntityKind.REPORT, EntityKind.WORKFLOW, EntityKind.READINESS):
        assert counts[kind.value] >= 1


# --- T3-I: readiness ---------------------------------------------------------
def test_readiness_reaches_ready_for_users():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    body = client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                       headers={"Authorization": f"Bearer {tok}"}).json()
    assert body["readiness"]["classification"] == ApplicationReadinessClass.READY_FOR_USERS.value
    rd = client.get("/v1/readiness", params={"analysis_id": body["analysis_id"]})
    assert rd.json()["classification"] == "READY_FOR_USERS"


# --- T3-J: audit + lineage ---------------------------------------------------
def test_audit_verifies():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                headers={"Authorization": f"Bearer {tok}"})
    assert svc.audit.verify() and len(svc.audit) >= 4


def test_lineage_chain_dataset_to_report():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    aid = client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                      headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
    outcome = svc.get_analysis(aid)
    node = outcome.report_record.lineage_id
    assert svc.lineage.verify_chain(node)
    kinds = {n.kind for n in svc.lineage.chain(node)}
    required = {"app_upload", "app_model_ref", "app_prediction_request",
                "app_prediction_result", "app_report"}
    assert required <= kinds


def test_entity_contract_validation():
    svc = make_product()
    client = make_client(svc)
    tok = _auth(client)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    aid = client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                      headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
    outcome = svc.get_analysis(aid)
    ok, missing = validate_entity("PredictionResultRecord", outcome.prediction_result.to_dict())
    assert ok and missing == []
    ok2, _ = validate_entity("UploadRecord", outcome.upload.to_dict())
    assert ok2


# --- determinism -------------------------------------------------------------
def test_determinism_across_instances():
    svc_a = make_product()
    ca = make_client(svc_a)
    tok_a = _auth(ca)
    b64 = base64.b64encode(real_eeg_bytes()).decode()
    a = ca.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                headers={"Authorization": f"Bearer {tok_a}"}).json()

    svc_b = make_product()
    cb = make_client(svc_b)
    tok_b = _auth(cb)
    b = cb.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                headers={"Authorization": f"Bearer {tok_b}"}).json()

    assert a["upload"]["upload_id"] == b["upload"]["upload_id"]
    assert a["analysis_id"] == b["analysis_id"]
    assert a["prediction"]["prediction_result_id"] == b["prediction"]["prediction_result_id"]
    assert a["prediction"]["predicted_label"] == b["prediction"]["predicted_label"]
