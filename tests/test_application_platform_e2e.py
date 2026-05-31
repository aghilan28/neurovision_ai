"""Track 3 end-to-end: the full Real Product Application deliverable.

Drives the complete user workflow over the **real** HTTP API (FastAPI ``TestClient``) +
**real EEG** (committed real EDF fixtures, network-free):

    register -> login -> upload real EEG -> validate -> analyze -> predict ->
    report (JSON/HTML/PDF) -> readiness READY_FOR_USERS, fully traceable.

A real-corpus variant runs over the locally-acquired CHB-MIT recordings when available.
"""

from __future__ import annotations

import base64
import os

import pytest

from _track3_helpers import make_client, make_product, real_chb_mit_root, real_eeg_bytes

from backend.application_platform import ApplicationPlatformService
from backend.model_foundation import ModelArchitecture
from backend.application_platform.uploads import prepare_bounded_segment


def test_complete_user_workflow_end_to_end():
    svc = make_product()
    client = make_client(svc)
    client.post("/v1/auth/register", json={"username": "dr", "password": "pw-123456",
                                           "roles": ["clinician"]})
    token = client.post("/v1/auth/login",
                        json={"username": "dr", "password": "pw-123456"}).json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}

    b64 = base64.b64encode(real_eeg_bytes()).decode()
    up = client.post("/v1/uploads", json={"filename": "valid_edf_plus.edf", "content_base64": b64},
                     headers=hdr)
    assert up.status_code == 201
    body = up.json()
    aid = body["analysis_id"]

    # a real EEG file was uploaded, a prediction generated, a report generated
    assert body["accepted"] and body["prediction"]["predicted_label"] != ""
    assert client.get(f"/v1/analyses/{aid}/prediction").status_code == 200
    assert client.get(f"/v1/analyses/{aid}/reports",
                      params={"type": "analysis", "format": "json"}).status_code == 200
    assert client.get(f"/v1/analyses/{aid}/reports",
                      params={"type": "evidence", "format": "pdf"}).content[:5] == b"%PDF-"

    # readiness READY_FOR_USERS + fully traceable
    assert body["readiness"]["classification"] == "READY_FOR_USERS"
    outcome = svc.get_analysis(aid)
    assert svc.lineage.verify_chain(outcome.report_record.lineage_id)
    assert svc.audit.verify()
    assert outcome.validation.ok


def test_real_corpus_user_workflow_when_available():
    root = real_chb_mit_root()
    if root is None:
        pytest.skip("real CHB-MIT corpus not acquired locally")
    # prepare a model from bounded segments of the genuine PhysioNet recordings
    svc = ApplicationPlatformService(analysis_seconds=20.0)
    chb = os.path.join(root, "chb_mit", "chb01")
    segs = []
    cohort = []
    for i, name in enumerate(("chb01_01.edf", "chb01_03.edf")):
        with open(os.path.join(chb, name), "rb") as fh:
            seg, _fp, _sz = prepare_bounded_segment(fh.read(), name, analysis_seconds=20.0)
        segs.append(seg)
        cohort.append((f"p{i}", f"c{i}", seg))
    try:
        svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
    finally:
        for s in segs:
            if os.path.exists(s):
                os.remove(s)
    client = make_client(svc)
    client.post("/v1/auth/register", json={"username": "dr", "password": "pw-123456"})
    token = client.post("/v1/auth/login",
                        json={"username": "dr", "password": "pw-123456"}).json()["token"]
    with open(os.path.join(chb, "chb01_03.edf"), "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    body = client.post("/v1/uploads", json={"filename": "chb01_03.edf", "content_base64": b64},
                       headers={"Authorization": f"Bearer {token}"}).json()
    assert body["accepted"] and body["readiness"]["classification"] == "READY_FOR_USERS"
    assert body["upload"]["n_channels"] == 23 and body["upload"]["sampling_frequency"] == 256.0
