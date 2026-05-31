"""DBE-5 — Authentication Failure & Invalid Token Reliability tests.

Proves the deployment blocker is eliminated: **no invalid-token or authorization-failure
path can produce an HTTP 500**. Every invalid credential class returns a *controlled*,
documented 401/403 with the deterministic response schema, and security audit events are
generated for failures while the audit chain stays valid.

Uses the **real** product (real model from the committed EDF fixtures), the **real** FastAPI
HTTP surface, and the **real** operative auth (``application_backend.auth``) reused by the
DBE-5 hardening — no mocks.
"""

from __future__ import annotations

import base64
import json

import pytest

from fastapi.testclient import TestClient

from _track3_helpers import make_client, make_product, real_eeg_bytes

from backend.application_platform import create_app
from backend.application_platform.security import (
    TokenFailureCode, assess_security_readiness, classify_request,
)
from backend.application_backend.models.domain import ApiOperation


# --- helpers -----------------------------------------------------------------
def _register_login(client, username="alice", password="pw-123456", roles=("clinician",)):
    client.post("/v1/auth/register", json={"username": username, "password": password,
                                            "roles": list(roles)})
    return client.post("/v1/auth/login",
                       json={"username": username, "password": password}).json()["token"]


def _b64_eeg() -> str:
    return base64.b64encode(real_eeg_bytes()).decode()


def _b64url(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _make_jwt(payload: dict, *, header=None, signature="ZmFrZQ") -> str:
    """Build a JWT-shaped (foreign/forged) token — the platform never issues JWTs."""
    header = header or {"alg": "HS256", "typ": "JWT"}
    return f"{_b64url(header)}.{_b64url(payload)}.{signature}"


def _upload(client, token=None, *, filename="valid_edf_plus.edf"):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.post("/v1/uploads",
                       json={"filename": filename, "content_base64": _b64_eeg()},
                       headers=headers)


# A single real product/client reused across read-only auth tests (model prep is the slow
# part; invalid-token requests never mutate state).
@pytest.fixture(scope="module")
def product():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    return svc, client


# =============================================================================
# DBE5-A/D: every invalid-token class returns a controlled response (no 500)
# =============================================================================
def test_missing_token_returns_401(product):
    _svc, client = product
    r = _upload(client, token=None)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.MISSING_TOKEN.value


def test_empty_token_returns_401(product):
    _svc, client = product
    r = client.post("/v1/uploads", json={"filename": "x.edf", "content_base64": _b64_eeg()},
                    headers={"Authorization": "Bearer "})
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.EMPTY_TOKEN.value


def test_malformed_token_returns_401(product):
    _svc, client = product
    r = _upload(client, token="!!!not-a-real-token!!!")
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.MALFORMED_TOKEN.value


def test_truncated_token_returns_401(product):
    _svc, client = product
    tok = _register_login(client)
    r = _upload(client, token=tok[: len(tok) // 2])  # half-length hex -> malformed shape
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.MALFORMED_TOKEN.value


def test_unknown_wellformed_token_returns_401(product):
    _svc, client = product
    r = _upload(client, token="00" * 32)  # 64-hex, correct shape, no live session
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.UNAUTHORIZED.value


def test_forged_token_returns_401(product):
    _svc, client = product
    tok = _register_login(client)
    forged = tok[:-4] + ("0000" if tok[-4:] != "0000" else "1111")
    r = _upload(client, token=forged)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.UNAUTHORIZED.value


def test_invalid_signature_jwt_returns_401(product):
    _svc, client = product
    # JWT claiming our issuer + audience, but we never sign JWTs -> INVALID_SIGNATURE.
    from backend.application_platform.security import EXPECTED_AUDIENCE, EXPECTED_ISSUER
    tok = _make_jwt({"iss": EXPECTED_ISSUER, "aud": EXPECTED_AUDIENCE, "sub": "x"})
    r = _upload(client, token=tok)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.INVALID_SIGNATURE.value


def test_invalid_issuer_jwt_returns_401(product):
    _svc, client = product
    tok = _make_jwt({"iss": "evil-issuer", "aud": "whatever", "sub": "x"})
    r = _upload(client, token=tok)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.INVALID_ISSUER.value


def test_invalid_audience_jwt_returns_401(product):
    _svc, client = product
    from backend.application_platform.security import EXPECTED_ISSUER
    tok = _make_jwt({"iss": EXPECTED_ISSUER, "aud": "some-other-service", "sub": "x"})
    r = _upload(client, token=tok)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.INVALID_AUDIENCE.value


def test_malformed_jwt_returns_401(product):
    _svc, client = product
    r = _upload(client, token="not.valid.jwt")  # 3 segments but not base64url JSON
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.MALFORMED_TOKEN.value


# =============================================================================
# DBE5-C: expired / revoked session
# =============================================================================
def test_expired_revoked_token_returns_401():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    tok = _register_login(client)
    # revoke the session through the real auth service (logout), then reuse the token.
    svc.backend.auth.revoke_session(token=tok)
    r = _upload(client, token=tok)
    assert r.status_code == 401
    assert r.json()["code"] == TokenFailureCode.EXPIRED_TOKEN.value


# =============================================================================
# DBE5-E: authorization failure (valid token, insufficient role) -> 403 FORBIDDEN
# =============================================================================
def test_unauthorized_role_is_forbidden_not_500():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    tok = _register_login(client, username="vic", roles=("viewer",))  # read-only role
    r = _upload(client, token=tok)
    assert r.status_code == 403
    body = r.json()
    assert body["code"] == TokenFailureCode.FORBIDDEN.value
    assert body["error"] == "forbidden"


# =============================================================================
# DBE5: the protected endpoint remains functional for a valid, authorized user
# =============================================================================
def test_protected_endpoint_still_works_for_valid_user():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    tok = _register_login(client)
    r = _upload(client, token=tok)
    assert r.status_code in (200, 201)
    assert r.json()["accepted"] is True


# =============================================================================
# DBE5: NO invalid-token path can ever produce a 500 (captured, not raised)
# =============================================================================
def test_no_invalid_token_path_returns_500():
    svc = make_product(analysis_seconds=2.0)
    # raise_server_exceptions=False => a 500 would surface as a status code, not an exception.
    client = TestClient(create_app(svc), raise_server_exceptions=False)
    valid = _register_login(client)
    from backend.application_platform.security import EXPECTED_AUDIENCE, EXPECTED_ISSUER
    forged = valid[:-4] + ("0000" if valid[-4:] != "0000" else "1111")  # guaranteed-different
    tokens = [
        None, "", "Bearer", "!!!bad!!!", valid[:10], "00" * 32,
        forged, "deadbeef", "a.b.c", "not.valid.jwt",
        _make_jwt({"iss": EXPECTED_ISSUER, "aud": EXPECTED_AUDIENCE}),
        _make_jwt({"iss": "evil", "aud": "evil"}),
    ]
    for tok in tokens:
        headers = {} if tok is None else {"Authorization": tok if tok.startswith("Bearer")
                                          else f"Bearer {tok}"}
        r = client.post("/v1/uploads",
                        json={"filename": "x.edf", "content_base64": _b64_eeg()},
                        headers=headers)
        assert r.status_code in (401, 403), f"token {tok!r} -> {r.status_code} (expected 401/403)"
        assert r.status_code != 500


# =============================================================================
# DBE5-F: security audit events are generated + the audit chain stays valid
# =============================================================================
def test_security_audit_events_generated_and_chain_valid():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    before = len(svc.audit)
    _upload(client, token="00" * 32)          # UNAUTHORIZED  -> authentication_failed
    _upload(client, token="!!!bad!!!")         # MALFORMED     -> authentication_failed
    tok = _register_login(client, username="vic", roles=("viewer",))
    _upload(client, token=tok)                 # FORBIDDEN     -> authorization_denied
    assert svc.audit.verify() is True
    kinds = [e.kind for e in svc.audit.events()[before:]]
    assert "authentication_failed" in kinds
    assert "authorization_denied" in kinds
    # the audit payload must never carry the raw token (only a fingerprint).
    for e in svc.audit.events()[before:]:
        if e.kind in ("authentication_failed", "authorization_denied"):
            assert "token" not in e.payload
            assert set(e.payload).issuperset({"code", "operation", "http_status"})


# =============================================================================
# DBE5-C: classification is deterministic + never raises
# =============================================================================
def test_classification_is_deterministic():
    svc_a = make_product(analysis_seconds=2.0)
    svc_b = make_product(analysis_seconds=2.0)
    for header in (None, "Bearer ", "Bearer !!!", "Bearer " + "00" * 32, "Bearer a.b.c"):
        ca = classify_request(auth_service=svc_a.backend.auth, authorization=header,
                              operation=ApiOperation.UPLOAD_EEG)
        cb = classify_request(auth_service=svc_b.backend.auth, authorization=header,
                              operation=ApiOperation.UPLOAD_EEG)
        assert ca.code == cb.code
        assert ca.http_status == cb.http_status in (401, 403)


def test_classifier_never_raises_on_hostile_input():
    svc = make_product(analysis_seconds=2.0)
    hostile = [None, "", "   ", "Bearer", "Bearer ", "Bearer\t", "\x00\x01", "." * 5,
               "a." * 50, "Bearer " + "Z" * 5000, "Bearer " + "💣🔥", "Bearer ..", "Bearer a..b"]
    for h in hostile:
        c = classify_request(auth_service=svc.backend.auth, authorization=h,
                             operation=ApiOperation.UPLOAD_EEG)
        assert c.code is not None  # always classified, never an exception
        assert c.http_status in (401, 403)


def test_classify_session_token_states():
    svc = make_product(analysis_seconds=2.0)
    client = make_client(svc)
    auth = svc.backend.auth
    assert auth.classify_session_token("")[0] == "unknown"
    assert auth.classify_session_token("00" * 32)[0] == "unknown"
    tok = _register_login(client)
    assert auth.classify_session_token(tok)[0] == "active"
    svc.backend.auth.revoke_session(token=tok)
    assert auth.classify_session_token(tok)[0] == "revoked"


# =============================================================================
# DBE5-G: security readiness
# =============================================================================
def test_security_readiness_is_ready():
    svc = make_product(analysis_seconds=2.0)
    report = assess_security_readiness(svc)
    assert report.ready is True
    assert report.classification == "READY"
    assert report.authentication_ready and report.authorization_ready
    assert report.protected_endpoint_ready


# =============================================================================
# regression: the controlled body never leaks a stack trace or internal text
# =============================================================================
def test_controlled_body_has_no_stack_trace(product):
    _svc, client = product
    r = _upload(client, token="!!!bad!!!")
    text = r.text.lower()
    assert "traceback" not in text and "workflowerror" not in text
    assert "internal server error" not in text
    body = r.json()
    assert set(body) == {"error", "code", "message", "status", "operation"}
