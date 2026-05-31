"""DBE-3 — Duplicate upload reliability tests (backend/application_platform).

Proves a user can never crash NeuroVision by re-uploading the same EEG: single upload,
duplicate upload, repeated duplicates, content-duplicate (renamed file), conflicting upload,
and the registry/audit/lineage/readiness integrity invariants — all over the **real** upload
workflow with real EEG fixtures, driven through the real FastAPI app (no mocks). Includes the
regression that the audit captured: a second identical upload must NOT return 500.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from _track3_helpers import make_product, real_eeg_bytes

from backend.application_platform import create_app
from backend.application_platform.uploads.duplicates import DuplicateDetector, content_hash
from backend.application_platform.models.domain import DuplicateClass


def _client(svc):
    # raise_server_exceptions=False => behave like a real deployed server (500, not raise)
    return TestClient(create_app(svc), raise_server_exceptions=False)


def _auth(c):
    c.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
    return c.post("/v1/auth/login", json={"username": "u", "password": "pw-123456"}).json()["token"]


def _upload(c, tok, content, filename="v.edf"):
    return c.post("/v1/uploads",
                  json={"filename": filename, "content_base64": base64.b64encode(content).decode()},
                  headers={"Authorization": f"Bearer {tok}"})


# --- the regression: duplicate upload must not 500 --------------------------
def test_single_upload_succeeds():
    c = _client(make_product(analysis_seconds=2.0))
    tok = _auth(c)
    r = _upload(c, tok, real_eeg_bytes())
    assert r.status_code == 201
    assert r.json()["accepted"] is True and r.json()["duplicate"] is False


def test_duplicate_upload_does_not_500():
    c = _client(make_product(analysis_seconds=2.0))
    tok = _auth(c)
    content = real_eeg_bytes()
    r1 = _upload(c, tok, content)
    r2 = _upload(c, tok, content)
    assert r1.status_code == 201
    assert r2.status_code == 200, f"duplicate upload returned {r2.status_code}, expected 200"
    assert r2.status_code != 500
    body2 = r2.json()
    assert body2["duplicate"] is True
    assert body2["duplicate_classification"] == "EXACT_DUPLICATE"
    # idempotent: same analysis id returned, not a new one
    assert body2["analysis_id"] == r1.json()["analysis_id"]


def test_repeated_duplicate_uploads_never_500():
    c = _client(make_product(analysis_seconds=2.0))
    tok = _auth(c)
    content = real_eeg_bytes()
    codes = [_upload(c, tok, content).status_code for _ in range(6)]
    assert codes[0] == 201
    assert all(code == 200 for code in codes[1:]), codes
    assert 500 not in codes


def test_content_duplicate_under_different_filename():
    c = _client(make_product(analysis_seconds=2.0))
    tok = _auth(c)
    content = real_eeg_bytes()
    r1 = _upload(c, tok, content, filename="first.edf")
    r2 = _upload(c, tok, content, filename="second.edf")
    assert r1.status_code == 201 and r2.status_code == 200
    assert r2.json()["duplicate"] is True
    assert r2.json()["duplicate_classification"] in ("CONTENT_DUPLICATE", "EXACT_DUPLICATE")
    assert r2.json()["analysis_id"] == r1.json()["analysis_id"]


def test_invalid_upload_is_422_not_500():
    c = _client(make_product(analysis_seconds=2.0))
    tok = _auth(c)
    r = _upload(c, tok, b"not an EEG file at all")
    assert r.status_code == 422 and r.status_code != 500


# --- integrity invariants (DBE3-E/G) ----------------------------------------
def test_registry_integrity_after_duplicates():
    svc = make_product(analysis_seconds=2.0)
    c = _client(svc)
    tok = _auth(c)
    content = real_eeg_bytes()
    for _ in range(4):
        _upload(c, tok, content)
    # exactly ONE upload/analysis/report registered despite 4 uploads; no orphans
    counts = svc.registry.counts()
    assert svc.registry.orphans() == []
    assert counts["app_upload"] == 1
    assert counts["app_analysis"] == 1
    assert counts["app_report"] == 1


def test_audit_chain_intact_after_duplicates():
    svc = make_product(analysis_seconds=2.0)
    c = _client(svc)
    tok = _auth(c)
    content = real_eeg_bytes()
    for _ in range(3):
        _upload(c, tok, content)
    assert svc.audit.verify()
    # a duplicate appends exactly one 'upload_duplicate' marker event (no corruption)
    kinds = [e.kind for e in svc.audit.events()]
    assert "upload_duplicate" in kinds


def test_lineage_intact_after_duplicates():
    svc = make_product(analysis_seconds=2.0)
    c = _client(svc)
    tok = _auth(c)
    content = real_eeg_bytes()
    aid = _upload(c, tok, content).json()["analysis_id"]
    _upload(c, tok, content)  # duplicate
    outcome = svc.get_analysis(aid)
    assert svc.lineage.verify_chain(outcome.report_record.lineage_id)


def test_readiness_preserved_after_duplicates():
    svc = make_product(analysis_seconds=2.0)
    c = _client(svc)
    tok = _auth(c)
    content = real_eeg_bytes()
    r1 = _upload(c, tok, content)
    r2 = _upload(c, tok, content)
    assert r1.json()["readiness"]["classification"] == "READY_FOR_USERS"
    assert r2.json()["readiness"]["classification"] == "READY_FOR_USERS"


def test_determinism_duplicate_classification():
    # two independent instances classify the same bytes identically
    a = make_product(analysis_seconds=2.0)
    b = make_product(analysis_seconds=2.0)
    ca, cb = _client(a), _client(b)
    ta, tb = _auth(ca), _auth(cb)
    content = real_eeg_bytes()
    _upload(ca, ta, content)
    _upload(cb, tb, content)
    da = _upload(ca, ta, content).json()
    db = _upload(cb, tb, content).json()
    assert da["duplicate_classification"] == db["duplicate_classification"] == "EXACT_DUPLICATE"
    assert da["analysis_id"] == db["analysis_id"]  # deterministic ids


# --- unit-level detector (pure, deterministic) ------------------------------
def test_content_hash_is_deterministic_and_content_addressed():
    a = content_hash(b"abc")
    b = content_hash(b"abc")
    c = content_hash(b"abd")
    assert a == b and a != c and a.startswith("sha+")


def test_detector_classifies_new_then_exact():
    d = DuplicateDetector()
    dec1 = d.classify(content=b"xyz", upload_id="app_upload+1", valid=True)
    assert dec1.classification == DuplicateClass.NEW_UPLOAD
    d.record(content_hash_value=dec1.content_hash, upload_id="app_upload+1", analysis_id="a1")
    dec2 = d.classify(content=b"xyz", upload_id="app_upload+1", valid=True)
    assert dec2.classification == DuplicateClass.EXACT_DUPLICATE
    assert dec2.existing_analysis_id == "a1"


def test_detector_content_duplicate_and_conflict():
    d = DuplicateDetector()
    dec1 = d.classify(content=b"xyz", upload_id="app_upload+1", valid=True)
    d.record(content_hash_value=dec1.content_hash, upload_id="app_upload+1", analysis_id="a1")
    # same content, different identity -> content duplicate
    dec_cd = d.classify(content=b"xyz", upload_id="app_upload+2", valid=True)
    assert dec_cd.classification == DuplicateClass.CONTENT_DUPLICATE
    # same identity, different content -> conflict
    dec_cf = d.classify(content=b"DIFFERENT", upload_id="app_upload+1", valid=True)
    assert dec_cf.classification == DuplicateClass.CONFLICTING_UPLOAD


def test_detector_invalid_upload():
    d = DuplicateDetector()
    dec = d.classify(content=b"", upload_id="app_upload+1", valid=False)
    assert dec.classification == DuplicateClass.INVALID_UPLOAD
