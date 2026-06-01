"""Final validation for DBE-5 — Authentication Failure & Invalid Token Reliability Fix.

Verifies the directive's 15 criteria against the **real** FastAPI app, the **real** operative
auth (``application_backend.auth``), and a real EEG fixture. It (1) reproduces the original
root cause (the deep workflow raises ``WorkflowError`` on a backend ``UNAUTHORIZED`` response,
which the old endpoint did not catch -> HTTP 500), then proves the hardened boundary now
classifies + handles every invalid-token / authorization-failure class with a controlled,
documented, non-500 response, generates security audit events, and preserves determinism +
repository boundaries.

    python -m scripts.verify_dbe5_authentication_reliability
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import base64
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def _b64url(obj: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(obj, sort_keys=True).encode()).decode().rstrip("=")


def _jwt(payload: dict, sig: str = "ZmFrZQ") -> str:
    return f"{_b64url({'alg': 'HS256', 'typ': 'JWT'})}.{_b64url(payload)}.{sig}"


def main() -> int:  # noqa: C901 - linear verification script
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    from fastapi.testclient import TestClient

    from backend.application_platform import create_app
    from backend.application_platform.security import (
        EXPECTED_AUDIENCE, EXPECTED_ISSUER, TokenFailureCode, assess_security_readiness,
        classify_request,
    )
    from backend.application_platform.uploads import prepare_bounded_segment
    from backend.application_platform.version import DETERMINISTIC_EPOCH
    from backend.application_platform.workflows import WorkflowError, run_backend_analysis
    from backend.application_backend.models.domain import ApiOperation
    from _track3_helpers import make_product, real_eeg_bytes

    content = real_eeg_bytes()
    b64 = base64.b64encode(content).decode()
    svc = make_product(analysis_seconds=2.0)

    # --- 1. Bug reproduced (the documented root cause) ---------------------------------
    # The deep workflow converts a backend UNAUTHORIZED response into a raised WorkflowError
    # (a RuntimeError). The OLD /v1/uploads endpoint did not catch it -> HTTP 500.
    try:
        seg, _fp, _sz = prepare_bounded_segment(content, "v.edf", analysis_seconds=2.0)
        reproduced = False
        try:
            run_backend_analysis(svc.backend, token="0" * 64, segment_path=seg, filename="v.edf",
                                 created_at=DETERMINISTIC_EPOCH)
        except WorkflowError:
            reproduced = True  # exactly the uncaught RuntimeError that became the 500
        check("1. Bug reproduced", reproduced,
              "invalid token in the deep workflow raises WorkflowError (the uncaught 500 source)")
    except Exception as exc:  # noqa: BLE001
        check("1. Bug reproduced", False, f"error: {exc}")

    # --- 2. Root cause identified (documented) -----------------------------------------
    doc = REPO / "backend" / "application_platform" / "docs" / "AUTHENTICATION_RELIABILITY.md"
    doc_txt = doc.read_text() if doc.exists() else ""
    check("2. Root cause identified",
          "WorkflowError" in doc_txt and "run_backend_analysis" in doc_txt and "500" in doc_txt,
          "root cause documented in AUTHENTICATION_RELIABILITY.md")

    # --- build the real product + drive the live API (capture 500s as status codes) ----
    client = TestClient(create_app(svc), raise_server_exceptions=False)

    def login(username="alice", roles=("clinician",)):
        client.post("/v1/auth/register",
                    json={"username": username, "password": "pw-123456", "roles": list(roles)})
        return client.post("/v1/auth/login",
                           json={"username": username, "password": "pw-123456"}).json()["token"]

    def upload(token=None, header=None):
        headers = {}
        if header is not None:
            headers["Authorization"] = header
        elif token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return client.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                           headers=headers)

    valid = login()

    def _forge(tok: str) -> str:
        # guaranteed-different forgery (random session tokens must never collide with valid)
        return tok[:-4] + ("0000" if tok[-4:] != "0000" else "1111")

    def code_of(resp):
        try:
            return resp.json().get("code")
        except Exception:  # noqa: BLE001
            return None

    # --- 3. Missing token handled ------------------------------------------------------
    r_missing = upload(token=None)
    check("3. Missing token handled",
          r_missing.status_code == 401 and code_of(r_missing) == TokenFailureCode.MISSING_TOKEN.value,
          f"{r_missing.status_code} {code_of(r_missing)}")

    # --- 4. Empty token handled --------------------------------------------------------
    r_empty = upload(header="Bearer ")
    check("4. Empty token handled",
          r_empty.status_code == 401 and code_of(r_empty) == TokenFailureCode.EMPTY_TOKEN.value,
          f"{r_empty.status_code} {code_of(r_empty)}")

    # --- 5. Malformed token handled ----------------------------------------------------
    r_malformed = upload(token="!!!not-a-token!!!")
    check("5. Malformed token handled",
          r_malformed.status_code == 401
          and code_of(r_malformed) == TokenFailureCode.MALFORMED_TOKEN.value,
          f"{r_malformed.status_code} {code_of(r_malformed)}")

    # --- 6. Invalid signature handled (foreign JWT) ------------------------------------
    r_sig = upload(token=_jwt({"iss": EXPECTED_ISSUER, "aud": EXPECTED_AUDIENCE}))
    r_iss = upload(token=_jwt({"iss": "evil", "aud": "evil"}))
    r_aud = upload(token=_jwt({"iss": EXPECTED_ISSUER, "aud": "other"}))
    check("6. Invalid signature handled",
          r_sig.status_code == 401 and code_of(r_sig) == TokenFailureCode.INVALID_SIGNATURE.value
          and code_of(r_iss) == TokenFailureCode.INVALID_ISSUER.value
          and code_of(r_aud) == TokenFailureCode.INVALID_AUDIENCE.value,
          f"sig={code_of(r_sig)} iss={code_of(r_iss)} aud={code_of(r_aud)}")

    # --- 7. Expired token handled (revoked session) -----------------------------------
    tok_rev = login(username="rev")
    svc.backend.auth.revoke_session(token=tok_rev)
    r_expired = upload(token=tok_rev)
    check("7. Expired token handled",
          r_expired.status_code == 401 and code_of(r_expired) == TokenFailureCode.EXPIRED_TOKEN.value,
          f"{r_expired.status_code} {code_of(r_expired)}")

    # --- 8. Authorization failures handled (viewer -> 403 FORBIDDEN) -------------------
    tok_viewer = login(username="viewer-user", roles=("viewer",))
    r_forbidden = upload(token=tok_viewer)
    check("8. Authorization failures handled",
          r_forbidden.status_code == 403 and code_of(r_forbidden) == TokenFailureCode.FORBIDDEN.value,
          f"{r_forbidden.status_code} {code_of(r_forbidden)}")

    # --- 9. No 500 responses (sweep every invalid-token class) -------------------------
    sweep_headers = [
        None, "Bearer ", "Bearer", "Bearer !!!", f"Bearer {valid[:10]}", "Bearer " + "00" * 32,
        f"Bearer {_forge(valid)}", "Bearer deadbeef", "Bearer a.b.c", "Bearer not.valid.jwt",
        f"Bearer {_jwt({'iss': EXPECTED_ISSUER, 'aud': EXPECTED_AUDIENCE})}",
        f"Bearer {_jwt({'iss': 'evil', 'aud': 'evil'})}", f"Bearer {tok_rev}", f"Bearer {tok_viewer}",
    ]
    statuses = []
    for h in sweep_headers:
        resp = upload(header=h) if h is not None else upload(token=None)
        statuses.append(resp.status_code)
    no_500 = all(s in (401, 403) for s in statuses)
    check("9. No 500 responses", no_500, f"statuses={sorted(set(statuses))} (all 401/403)")

    # --- 10. Security audit events generated (chain valid, no raw token) ---------------
    kinds = [e.kind for e in svc.audit.events()]
    no_raw_token = all("token" not in e.payload
                       for e in svc.audit.events()
                       if e.kind in ("authentication_failed", "authorization_denied"))
    check("10. Security audit events generated",
          svc.audit.verify() and "authentication_failed" in kinds
          and "authorization_denied" in kinds and no_raw_token,
          "authentication_failed + authorization_denied recorded; chain verifies; no raw token")

    # --- 13. Determinism preserved -----------------------------------------------------
    svc2 = make_product(analysis_seconds=2.0)
    same = True
    for h in ("Bearer !!!", "Bearer " + "00" * 32, f"Bearer {_jwt({'iss': 'x', 'aud': 'y'})}"):
        c1 = classify_request(auth_service=svc.backend.auth, authorization=h,
                              operation=ApiOperation.UPLOAD_EEG)
        c2 = classify_request(auth_service=svc2.backend.auth, authorization=h,
                              operation=ApiOperation.UPLOAD_EEG)
        same = same and (c1.code == c2.code) and (c1.http_status == c2.http_status)
    check("13. Determinism preserved", same, "identical classification across instances")

    # --- 14. Security behavior documented ----------------------------------------------
    documented = all(k in doc_txt for k in (
        "MISSING_TOKEN", "EMPTY_TOKEN", "MALFORMED_TOKEN", "INVALID_SIGNATURE", "INVALID_ISSUER",
        "INVALID_AUDIENCE", "EXPIRED_TOKEN", "UNAUTHORIZED", "FORBIDDEN", "UNKNOWN_TOKEN_FAILURE",
        "401", "403", "Authentication Failure Guide", "Security Operator Guide",
        "API Response Guide", "Token Validation Guide"))
    check("14. Security behavior documented", documented,
          "AUTHENTICATION_RELIABILITY.md documents all codes, statuses + the 4 guides")

    # --- readiness (informational, feeds completion) -----------------------------------
    readiness = assess_security_readiness(svc)
    check("Security readiness READY", readiness.ready, readiness.classification)

    # --- 11. tests pass ----------------------------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_dbe5_authentication_reliability.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("11. Tests pass", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved -------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_boundaries.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("12. Repository boundaries preserved", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- 15. DBE-5 completed ------------------------------------------------------------
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. DBE-5 completed", completed,
          "every invalid-token + authorization path returns a controlled, documented non-500 response")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 50))
    print("\nDBE-5 — AUTHENTICATION FAILURE & INVALID TOKEN RELIABILITY — FINAL VALIDATION")
    print("=" * 76)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 76)
    print(f"UPLOAD STATUSES across all invalid-token classes: {sorted(set(statuses))}  (no 500)")
    print("-" * 76)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
