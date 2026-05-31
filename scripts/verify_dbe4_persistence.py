"""Final validation for DBE-4 — Persistence Wiring & State Durability Fix.

Verifies the directive's 15 criteria against the **real** application + the real DRP-4 storage
backend over a real EEG fixture. It (1) reproduces the root cause (without persistence, state
is lost on restart), then (2) with persistence wired, runs upload -> predict -> report, performs
a real **restart** (a brand-new service at the same persistence root), and proves the upload /
prediction / report / analysis / readiness are retrievable from recovered state with registry /
audit / lineage references intact.

    python -m scripts.verify_dbe4_persistence
"""

from __future__ import annotations

import base64
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    from fastapi.testclient import TestClient

    from backend.application_platform import ApplicationPlatformService, create_app
    from backend.model_foundation import ModelArchitecture
    from _track3_helpers import real_eeg_bytes

    fixture_dir = REPO / "tests" / "fixtures" / "eeg"
    workdir = tempfile.mkdtemp(prefix="nv_dbe4_")
    state_root = os.path.join(workdir, "app_state")

    def build(persist: bool):
        svc = ApplicationPlatformService(
            persistence_root=state_root if persist else None, analysis_seconds=2.0)
        cohort = [("p-a", "c-a", str(fixture_dir / "valid.edf")),
                  ("p-b", "c-b", str(fixture_dir / "valid_edf_plus.edf"))]
        svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
        return svc

    def upload(svc, content=None):
        c = TestClient(create_app(svc), raise_server_exceptions=False)
        c.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
        tok = c.post("/v1/auth/login",
                     json={"username": "u", "password": "pw-123456"}).json()["token"]
        b64 = base64.b64encode(content or real_eeg_bytes()).decode()
        r = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": b64},
                   headers={"Authorization": f"Bearer {tok}"})
        return c, r

    # --- 1. Root cause reproduced (no persistence -> state lost on restart) ---
    try:
        eph1 = ApplicationPlatformService(analysis_seconds=2.0)
        eph1_cohort = [("p-a", "c-a", str(fixture_dir / "valid.edf")),
                       ("p-b", "c-b", str(fixture_dir / "valid_edf_plus.edf"))]
        eph1.prepare_model(eph1_cohort, architecture=ModelArchitecture.EEGNET)
        _c, r = upload(eph1)
        aid_eph = r.json()["analysis_id"]
        eph2 = ApplicationPlatformService(analysis_seconds=2.0)  # restart w/o persistence
        lost = False
        try:
            eph2.get_analysis(aid_eph)
        except KeyError:
            lost = True
        check("1. Root cause reproduced", lost and not eph1.persistence_enabled,
              "without persistence, analysis is lost after restart (the audit finding)")
    except Exception as exc:
        check("1. Root cause reproduced", False, f"error: {exc}")

    # --- build persistent product + run the workflow ---
    svc1 = build(persist=True)
    _c1, r1 = upload(svc1)
    body = r1.json()
    aid = body["analysis_id"]
    upload_id = body["upload"]["upload_id"]
    pred_id = body["prediction"]["prediction_result_id"]

    # --- 2. Persistence inventory complete (all mandatory entities serialized) ---
    try:
        from backend.application_platform.persistence import ApplicationStateStore
        store = ApplicationStateStore(state_root)
        payload = store.load_payload(aid)
        od = payload["outcome"]
        present = all(od.get(k) for k in ("upload", "analysis", "prediction_request",
                                          "prediction_result", "report", "readiness"))
        present = present and bool(payload.get("report_payloads")) and bool(payload.get("duplicate_index"))
        check("2. Persistence inventory complete", present,
              "upload/prediction(req+res)/analysis/report/readiness + reports persisted")
    except Exception as exc:
        check("2. Persistence inventory complete", False, f"error: {exc}")

    # --- RESTART: a fresh service at the same persistence root ---
    svc2 = build(persist=True)
    rep = svc2.recovery_report

    # --- 3/4/5. uploads/predictions/reports persisted (retrievable post-restart) ---
    try:
        check("3. Uploads persisted", svc2.get_upload(upload_id).upload_id == upload_id,
              f"upload {upload_id[:20]} recovered")
    except Exception as exc:
        check("3. Uploads persisted", False, f"error: {exc}")
    try:
        check("4. Predictions persisted", svc2.get_prediction(aid).prediction_result_id == pred_id,
              "prediction recovered with same id")
    except Exception as exc:
        check("4. Predictions persisted", False, f"error: {exc}")
    try:
        check("5. Reports persisted", svc2.get_report(aid).analysis_id == aid
              and bool(svc2.report_payloads(aid)),
              "report record + payloads recovered")
    except Exception as exc:
        check("5. Reports persisted", False, f"error: {exc}")

    # --- 6. Recovery works / 7. restart recovery works ---
    check("6. Recovery works", rep is not None and rep.ok and rep.n_analyses == 1,
          f"recovery report ok={getattr(rep, 'ok', None)} n_analyses={getattr(rep, 'n_analyses', None)}")
    try:
        # repeated restart stays stable
        svc3 = build(persist=True)
        check("7. Restart recovery works",
              svc3.recovery_report.ok and svc3.get_analysis(aid).analysis.analysis_id == aid,
              "second restart also recovers the analysis")
    except Exception as exc:
        check("7. Restart recovery works", False, f"error: {exc}")

    # --- 8. audit survives restart / 9. lineage survives restart ---
    try:
        out2 = svc2.get_analysis(aid)
        audit_ref = bool(out2.upload.audit_head)  # audit head reference persisted on the record
        check("8. Audit survives restart", audit_ref and svc2.audit.verify(),
              "audit-head references intact on recovered records; audit chain valid")
    except Exception as exc:
        check("8. Audit survives restart", False, f"error: {exc}")
    try:
        out2 = svc2.get_analysis(aid)
        lin_ref = bool(out2.report_record.lineage_id and out2.prediction_result.lineage_id
                       and out2.upload.lineage_id)
        check("9. Lineage survives restart", lin_ref,
              "lineage references intact on recovered upload/prediction/report")
    except Exception as exc:
        check("9. Lineage survives restart", False, f"error: {exc}")

    # --- 10. retrieval works after restart (via API) ---
    try:
        c2 = TestClient(create_app(svc2), raise_server_exceptions=False)
        ok = (c2.get(f"/v1/uploads/{upload_id}").status_code == 200
              and c2.get(f"/v1/analyses/{aid}").status_code == 200
              and c2.get(f"/v1/analyses/{aid}/prediction").status_code == 200
              and c2.get(f"/v1/analyses/{aid}/reports", params={"type": "analysis"}).status_code == 200)
        check("10. Retrieval works after restart", ok, "GET upload/analysis/prediction/report -> 200")
    except Exception as exc:
        check("10. Retrieval works after restart", False, f"error: {exc}")

    # --- 13. determinism preserved (recovered ids identical) ---
    try:
        out2 = svc2.get_analysis(aid)
        check("13. Determinism preserved",
              out2.analysis.analysis_id == aid and out2.prediction_result.prediction_result_id == pred_id,
              "recovered ids identical to originals (no reconstruction drift)")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. persistence documented ---
    doc = REPO / "backend" / "application_platform" / "docs" / "PERSISTENCE.md"
    doc_txt = doc.read_text() if doc.exists() else ""
    check("14. Persistence documented",
          "restart" in doc_txt.lower() and "recovery" in doc_txt.lower()
          and "NV_PERSISTENCE_DIR" in doc_txt,
          f"{doc.name} documents storage location + recovery + restart")

    # --- 11. tests pass ---
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_persistence_durability.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("11. Tests pass", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_boundaries.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("12. Repository boundaries preserved", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- 15. DBE-4 completed ---
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. DBE-4 completed", completed,
          "state durable across restart; retrieval works; integrity preserved")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDBE-4 — PERSISTENCE WIRING & STATE DURABILITY — FINAL VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 66)
    print(f"RESTART RECOVERY: persisted=1 analysis -> recovered={getattr(rep, 'n_analyses', '?')}; "
          f"retrievable upload/prediction/report after restart")
    print("-" * 66)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    # best-effort cleanup
    try:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
    except Exception:
        pass
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
