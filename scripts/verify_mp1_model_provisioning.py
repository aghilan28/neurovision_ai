"""Final validation for MP-1 — Model Provisioning Foundation.

Verifies the directive's 15 criteria against the **real** production ASGI app
(``server.app:app`` via ``build_application``), the real ``ApplicationPlatformService``, the
real provisioning path, and the committed real EDF fixture as a user upload. It (1) reproduces
the original root cause (a service with no provisioned model raises
``ApplicationPlatformError('no model prepared')`` and ``/readyz`` would report a model-less
"ready"), then proves a fresh startup provisions a deterministic model, readiness becomes
true, the upload->predict workflow succeeds (no 500), the model is registered with a valid
audit chain, and the model survives a restart with no manual step.

    python -m scripts.verify_mp1_model_provisioning
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import base64
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:  # noqa: C901 - linear verification script
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    from fastapi.testclient import TestClient

    from backend.application_platform import ApplicationPlatformService, ApplicationPlatformError
    from backend.application_platform import provision_model
    from backend.application_platform.server import build_application, load_config
    from _track3_helpers import real_eeg_bytes

    edf_b64 = base64.b64encode(real_eeg_bytes()).decode()

    def auth(client, username="op"):
        client.post("/v1/auth/register",
                    json={"username": username, "password": "pw-123456", "roles": ["clinician"]})
        return client.post("/v1/auth/login",
                           json={"username": username, "password": "pw-123456"}).json()["token"]

    # --- 1. Root cause reproduced: no provisioning -> upload raises "no model prepared" ----
    try:
        svc0 = ApplicationPlatformService()
        reproduced = False
        try:
            svc0.upload_and_analyze(token="x", filename="v.edf", content=real_eeg_bytes())
        except ApplicationPlatformError as exc:
            reproduced = "no model prepared" in str(exc)
        check("1. Root cause reproduced", reproduced,
              "service without provisioning raises ApplicationPlatformError('no model prepared')")
    except Exception as exc:  # noqa: BLE001
        check("1. Root cause reproduced", False, f"error: {exc}")

    # --- 2. Root cause identified (documented) ---------------------------------------------
    doc = REPO / "backend" / "application_platform" / "docs" / "MODEL_PROVISIONING.md"
    doc_txt = doc.read_text() if doc.exists() else ""
    check("2. Root cause identified",
          "build_application" in doc_txt and "_model_info" in doc_txt and "ready" in doc_txt,
          "root cause documented in MODEL_PROVISIONING.md")

    # --- 3. Model provisions on startup (fresh production app) -----------------------------
    _svc, app = build_application(load_config({}))
    with TestClient(app, raise_server_exceptions=False) as c:
        report = app.state.startup_report
        provisioned = bool(report.model_provisioned and report.model_id)
        check("3. Model provisions on startup", provisioned,
              f"source={report.provisioning_source} id={report.model_id}")

        # --- 4. Model registry updated ----------------------------------------------------
        mr = _svc.backend.model_context.model_record if _svc.backend.model_context else None
        registry_ok = mr is not None and bool(getattr(mr, "lineage_id", None))
        check("4. Model registry updated", registry_ok,
              f"model_record={getattr(mr, 'model_id', None)} lineage={bool(getattr(mr,'lineage_id',None))}")

        # --- 5. Readiness becomes true ----------------------------------------------------
        rz = c.get("/readyz").json()
        check("5. Readiness becomes true", rz["ready"] is True and rz["model_prepared"] is True,
              f"readyz={rz}")

        # --- 6. Upload succeeds (no 500) --------------------------------------------------
        tok = auth(c)
        up = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": edf_b64},
                    headers={"Authorization": f"Bearer {tok}"})
        check("6. Upload succeeds", up.status_code in (200, 201) and up.status_code != 500,
              f"status={up.status_code}")
        aid = up.json().get("analysis_id") if up.status_code in (200, 201) else None

        # --- 7. Prediction succeeds -------------------------------------------------------
        pred_ok = False
        if aid:
            pr = c.get(f"/v1/analyses/{aid}/prediction")
            rp = c.get(f"/v1/analyses/{aid}/reports")
            pred_ok = pr.status_code == 200 and rp.status_code == 200
        check("7. Prediction succeeds", pred_ok, f"analysis_id={aid}")

        # --- 10. No manual preparation required -------------------------------------------
        # (the only action taken above was starting the app + the user upload; no prepare_model)
        check("10. No manual preparation required", provisioned and up.status_code in (200, 201),
              "fresh start + upload worked with zero operator model steps")

    # --- 8/9. Restart recovery + persistence (same workspace) ------------------------------
    ws = tempfile.mkdtemp(prefix="nv_mp1_verify_ws_")
    cfg = load_config({"workspace_dir": ws})
    svc1, app1 = build_application(cfg)
    with TestClient(app1, raise_server_exceptions=False) as c:
        tok = auth(c)
        aid = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": edf_b64},
                     headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
        mid1 = svc1.backend.model_context.model_record.model_id
    svc2, app2 = build_application(cfg)
    with TestClient(app2, raise_server_exceptions=False) as c:
        rz2 = c.get("/readyz").json()
        mid2 = svc2.backend.model_context.model_record.model_id
        recovered = c.get(f"/v1/analyses/{aid}/reports").status_code == 200
        check("8. Restart recovery works", rz2["ready"] is True and recovered,
              f"ready={rz2['ready']} recovered_report={recovered}")
        check("9. Persistence works", mid1 == mid2 and svc2.audit.verify(),
              f"deterministic model_id across restart={mid1 == mid2}; audit_valid={svc2.audit.verify()}")

    # --- 13. Determinism preserved ---------------------------------------------------------
    a = ApplicationPlatformService()
    ra = provision_model(a)
    b = ApplicationPlatformService()
    rb = provision_model(b)
    check("13. Determinism preserved", ra.model_id == rb.model_id,
          f"model_id stable across instances: {ra.model_id}")

    # --- 14. Documentation complete --------------------------------------------------------
    documented = all(s in doc_txt for s in (
        "Model Provisioning Guide", "Startup Guide", "Recovery Guide", "Operator Guide",
        "NV_PROVISION_MODEL", "ready", "bootstrap"))
    check("14. Documentation complete", documented,
          "MODEL_PROVISIONING.md has the 4 guides + env + readiness + bootstrap")

    # --- 11. tests pass --------------------------------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_mp1_model_provisioning.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("11. Tests pass", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved -----------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_boundaries.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("12. Repository boundaries preserved", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- 15. MP-1 completed ----------------------------------------------------------------
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. MP-1 completed", completed,
          "fresh deploy provisions a model, reaches ready=true, and upload->predict works")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 50))
    print("\nMP-1 — MODEL PROVISIONING FOUNDATION — FINAL VALIDATION")
    print("=" * 76)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 76)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
