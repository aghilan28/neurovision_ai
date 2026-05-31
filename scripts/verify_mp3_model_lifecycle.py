"""Final validation for MP-3 — Persistent Model Lifecycle & Recovery Certification.

Verifies the directive's 15 criteria against the **real** production ASGI app
(``server.app:app`` via ``build_application``), the real ``ApplicationPlatformService``, the
real MP-1 provisioning path, and the real DBE-4 ``StorageEngine`` over temp workspaces — no
mocks. It proves a provisioned model **survives restart** with continuous identity, that the
registry / metadata / audit / lineage / readiness remain valid across the restart, that
failure conditions degrade in a controlled, honest way (no crash, no false-positive
readiness), and that the operator workflow (provision -> upload -> predict -> restart ->
recover -> predict) runs with no manual step.

    python -m scripts.verify_mp3_model_lifecycle
"""

from __future__ import annotations

import base64
import pathlib
import shutil
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

    from backend.application_platform import (
        ApplicationPlatformService, assess_recovery_readiness, current_model_identity,
        recover_model,
    )
    from backend.application_platform.lifecycle import ModelRecoveryReport
    from backend.application_platform.server import build_application, load_config
    from _track3_helpers import real_eeg_bytes

    edf_b64 = base64.b64encode(real_eeg_bytes()).decode()

    def auth(client, username="op"):
        client.post("/v1/auth/register",
                    json={"username": username, "password": "pw-123456", "roles": ["clinician"]})
        return client.post("/v1/auth/login",
                           json={"username": username, "password": "pw-123456"}).json()["token"]

    doc = REPO / "backend" / "application_platform" / "docs" / "MODEL_LIFECYCLE.md"
    doc_txt = doc.read_text() if doc.exists() else ""

    # --- 1. Lifecycle inventory complete ---------------------------------------------------
    # The seven lifecycle stages are documented AND the runtime exposes the recovery primitives.
    stages = ("Model Creation", "Model Registration", "Model Provisioning", "Model Persistence",
              "Model Recovery", "Model Consumption", "Model Retirement")
    rep_fields = set(ModelRecoveryReport.__dataclass_fields__)
    inventory_ok = (all(s in doc_txt for s in stages)
                    and {"recovered", "model_available", "identity_continuous",
                         "persistence_ok"} <= rep_fields)
    check("1. Lifecycle inventory complete", inventory_ok,
          "seven stages documented + ModelRecoveryReport exposes the lifecycle signals")

    # --- 2. Persistence audited ------------------------------------------------------------
    # Durable model identity is persisted (NOT weights) on the shared StorageEngine.
    ws2 = tempfile.mkdtemp(prefix="nv_mp3_persist_")
    svc2 = ApplicationPlatformService(workspace_dir=ws2)
    rep2 = recover_model(svc2)
    stored = svc2._state_store.load_model_identity()
    persistence_ok = (rep2.identity_persisted and stored is not None
                      and stored.get("model_id") == rep2.model_id
                      and "Persistence Reality Report" in doc_txt)
    check("2. Persistence audited", persistence_ok,
          f"durable model identity persisted: {stored.get('model_id') if stored else None}")

    # --- 3. Recovery audited ---------------------------------------------------------------
    recovery_audited = ("Recovery Reality Report" in doc_txt
                        and isinstance(rep2, ModelRecoveryReport) and rep2.recovered)
    check("3. Recovery audited", recovery_audited,
          "recovery path documented + ModelRecoveryReport produced")

    # --- 4./5./6./7./8./9. survive restart -------------------------------------------------
    ws = tempfile.mkdtemp(prefix="nv_mp3_restart_")
    cfg = load_config({"workspace_dir": ws})

    svc_a, app_a = build_application(cfg)
    with TestClient(app_a, raise_server_exceptions=False) as c:
        tok = auth(c)
        aid = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": edf_b64},
                     headers={"Authorization": f"Bearer {tok}"}).json()["analysis_id"]
        mid1 = svc_a.backend.model_context.model_record.model_id
        ident1 = current_model_identity(svc_a)

    svc_b, app_b = build_application(cfg)
    with TestClient(app_b, raise_server_exceptions=False) as c:
        rz = c.get("/readyz").json()
        recB = svc_b.model_recovery_report
        mid2 = svc_b.backend.model_context.model_record.model_id
        ident2 = current_model_identity(svc_b)
        report_recovered = c.get(f"/v1/analyses/{aid}/reports").status_code == 200

        check("4. Model survives restart",
              mid1 == mid2 and recB.recovered_from_persistence and recB.identity_continuous,
              f"model_id stable across restart: {mid1 == mid2}")
        check("5. Registry survives restart",
              recB.registered and report_recovered and svc_b.recovery_report.ok,
              "model re-registered + prior analysis recovered (orphan-free registry)")
        check("6. Metadata survives restart",
              ident2 == ident1 and ident2.get("architecture") == "eegnet",
              f"identity/metadata identical: {ident2.get('model_id')}")
        check("7. Audit survives restart", svc_b.audit.verify() is True,
              "shared audit chain verifies after restart")
        check("8. Lineage survives restart",
              recB.lineage_ok and svc_b.lineage.verify_chain(ident2["lineage_id"]),
              "model lineage node recreated + verify_chain holds")
        check("9. Readiness survives restart",
              rz["ready"] is True and rz["model_recovered"] is True,
              f"readyz after restart={rz}")

    # --- 10. Failure recovery validated ----------------------------------------------------
    # (a) persistence unavailable -> honest ready=false, no crash, model still usable in-process
    wsf = tempfile.mkdtemp(prefix="nv_mp3_fail_")
    svcf = ApplicationPlatformService(workspace_dir=wsf)
    recover_model(svcf)
    root = svcf._state_store.root
    shutil.rmtree(root)
    pathlib.Path(root).write_text("not-a-dir")          # genuine ENOTDIR failure
    repf = recover_model(svcf)                            # must not raise
    ready_f, reasons_f = assess_recovery_readiness(startup_ok=True, recovery=repf)
    persistence_fail_ok = (repf.persistence_ok is False and ready_f is False
                           and "persistence_unavailable" in reasons_f
                           and repf.model_available is True)
    # (b) identity discontinuity -> detected, ready=false
    wsd = tempfile.mkdtemp(prefix="nv_mp3_disc_")
    s1 = ApplicationPlatformService(workspace_dir=wsd)
    recover_model(s1)
    s1._state_store.persist_model_identity({
        "model_id": "model+DEADBEEFDEADBEEF", "architecture": "eegnet", "lineage_id": None,
        "dataset_key": "nv-bootstrap", "source": "bootstrap_cohort", "version": "x",
        "created_at": "1970-01-01T00:00:00Z"})
    s2 = ApplicationPlatformService(workspace_dir=wsd)
    repd = recover_model(s2)
    disc_ok = repd.identity_continuous is False and repd.recovered is False
    # (c) corrupt durable identity -> tolerated, re-established
    wsc = tempfile.mkdtemp(prefix="nv_mp3_corrupt_")
    sc = ApplicationPlatformService(workspace_dir=wsc)
    recover_model(sc)
    with open(sc._state_store.engine._path("app.model", "provisioned"), "wb") as fh:
        fh.write(b"{ not json ")
    corrupt_tolerated = sc._state_store.load_model_identity() is None
    sc2 = ApplicationPlatformService(workspace_dir=wsc)
    corrupt_reestablished = recover_model(sc2).recovered is True
    check("10. Failure recovery validated",
          persistence_fail_ok and disc_ok and corrupt_tolerated and corrupt_reestablished,
          "persistence-unavailable + identity-discontinuity + corruption all controlled")

    # --- 11. Operator workflow validated ---------------------------------------------------
    wso = tempfile.mkdtemp(prefix="nv_mp3_op_")
    cfgo = load_config({"workspace_dir": wso})
    svc1, app1 = build_application(cfgo)
    with TestClient(app1, raise_server_exceptions=False) as c:
        tok = auth(c)
        up1 = c.post("/v1/uploads", json={"filename": "v.edf", "content_base64": edf_b64},
                     headers={"Authorization": f"Bearer {tok}"})
        aid1 = up1.json()["analysis_id"]
        pred1 = c.get(f"/v1/analyses/{aid1}/prediction").status_code
    svc2b, app2b = build_application(cfgo)
    with TestClient(app2b, raise_server_exceptions=False) as c:
        ready_again = c.get("/readyz").json()["ready"]
        tok = auth(c, username="op2")
        up2 = c.post("/v1/uploads", json={"filename": "v2.edf", "content_base64": edf_b64},
                     headers={"Authorization": f"Bearer {tok}"})
        aid2 = up2.json()["analysis_id"]
        pred2 = c.get(f"/v1/analyses/{aid2}/prediction").status_code
        same_model = svc2b.backend.model_context.model_record.model_id == \
            svc1.backend.model_context.model_record.model_id
    operator_ok = (up1.status_code in (200, 201) and pred1 == 200 and ready_again
                   and up2.status_code in (200, 201) and pred2 == 200 and same_model)
    check("11. Operator workflow validated", operator_ok,
          "provision -> upload -> predict -> RESTART -> recover -> upload -> predict (no manual step)")

    # --- 12. Tests pass --------------------------------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_mp3_model_lifecycle.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("12. Tests pass", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("12. Tests pass", False, f"error: {exc}")

    # --- 13. Documentation complete --------------------------------------------------------
    documented = all(s in doc_txt for s in (
        "Model Lifecycle Guide", "Recovery Guide", "Persistence Guide", "Operator Restart Guide",
        "Failure Recovery Guide", "Lifecycle Inventory Report", "Persistence Reality Report",
        "Recovery Reality Report", "NV_PROVISION_MODEL"))
    check("13. Documentation complete", documented,
          "MODEL_LIFECYCLE.md has the 5 guides + the audit reports")

    # --- 14. Boundaries preserved ----------------------------------------------------------
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_boundaries.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("14. Boundaries preserved", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:  # noqa: BLE001
        check("14. Boundaries preserved", False, f"error: {exc}")

    # --- 15. MP-3 completed ----------------------------------------------------------------
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. MP-3 completed", completed,
          "provisioned model survives restart, recovery is automatic, identity/registry/audit/"
          "lineage/readiness remain valid, and readiness stays honest")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 50))
    print("\nMP-3 — PERSISTENT MODEL LIFECYCLE & RECOVERY — FINAL VALIDATION")
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
