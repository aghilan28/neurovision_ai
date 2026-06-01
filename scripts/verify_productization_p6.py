"""Final validation for Productization P6 — Application Backend Platform.

Objectively verifies the directive's 15 phase-completion criteria: that the platform's
P1-P5 capabilities are exposed through governed application backend services so a user
can authenticate, upload a real EEG file, trigger analysis, and retrieve a prediction +
confidence + explanation — registered, audited, validated, traced
(User -> Upload -> EEG -> Processed -> Feature -> Model -> Prediction), and deterministic,
with the test suite green and repository boundaries intact.

    python -m scripts.verify_productization_p6
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    import _eeg_fixtures as fx
    from backend.model_foundation import ModelArchitecture
    from backend.application_backend import (
        ApplicationBackendService, ApiRequest, ApiOperation, ResponseStatus, SessionStatus,
        UserRole, UserStatus, WorkflowStatus, WorkflowStage, EntityKind, DeterministicEntropy,
    )

    tmp = tempfile.mkdtemp(prefix="nv_app_p6_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))
    names = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
    cohort = [(f"P-{i}", f"C-{i}", fixtures[n]) for i, n in enumerate(names)]

    svc = ApplicationBackendService(workspace_dir=str(pathlib.Path(tmp) / "ws"),
                                    entropy=DeterministicEntropy("verify"))
    svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7)
    api = svc.api

    # --- 1. authentication works ---
    try:
        reg = api.handle(ApiRequest(ApiOperation.REGISTER_USER, {
            "username": "dr.verify", "password": "verify-pass-1", "roles": ["clinician"]}))
        login = api.handle(ApiRequest(ApiOperation.LOGIN,
                                     {"username": "dr.verify", "password": "verify-pass-1"}))
        token = login.body.get("token")
        bad = api.handle(ApiRequest(ApiOperation.LOGIN,
                                   {"username": "dr.verify", "password": "wrong"}))
        ok = (reg.status == ResponseStatus.CREATED and login.status == ResponseStatus.OK
              and bool(token) and bad.status == ResponseStatus.UNAUTHORIZED)
        check("1. Authentication works", ok,
              f"register={reg.status.value} login={login.status.value} bad_login={bad.status.value}")
    except Exception as exc:
        check("1. Authentication works", False, f"error: {exc}")
        token = None

    # --- 2. sessions work ---
    try:
        session = svc.auth.validate_session(token)
        revoked_result = svc.auth.login(username="dr.verify", password="verify-pass-1")
        svc.auth.revoke_session(token=revoked_result.token)
        ok = (session is not None and session.status == SessionStatus.ACTIVE
              and svc.auth.validate_session(revoked_result.token) is None)
        check("2. Sessions work", ok,
              f"active={session.status.value if session else None} revoke_invalidates=True")
    except Exception as exc:
        check("2. Sessions work", False, f"error: {exc}")

    # --- 3. user management works ---
    try:
        u = svc.users.create_user(username="nurse.joy", roles=[UserRole.VIEWER])
        upd = svc.users.update_user(u.user_id, roles=[UserRole.CLINICIAN])
        deact = svc.users.deactivate_user(u.user_id)
        log = svc.users.audit_log_for(u.user_id)
        ok = (UserRole.CLINICIAN in upd.roles and deact.status == UserStatus.DEACTIVATED
              and log.verify() and len(svc.users.list_users()) >= 2)
        check("3. User management works", ok,
              f"users={len(svc.users.list_users())} audit_ok={log.verify()}")
    except Exception as exc:
        check("3. User management works", False, f"error: {exc}")

    # --- 4. upload workflow works ---
    try:
        with open(fixtures[fx.VALID_EDF], "rb") as fh:
            content = fh.read()
        up = api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                  {"filename": "rec.edf", "content": content}, token=token))
        upload_id = up.body.get("upload_id")
        listing = api.handle(ApiRequest(ApiOperation.LIST_EEG, {}, token=token))
        retrieve = api.handle(ApiRequest(ApiOperation.RETRIEVE_EEG, {"upload_id": upload_id}, token=token))
        ok = (up.status == ResponseStatus.CREATED and bool(upload_id)
              and listing.ok and retrieve.ok)
        check("4. Upload workflow works", ok,
              f"upload={up.status.value} size={up.body.get('size_bytes')}")
    except Exception as exc:
        check("4. Upload workflow works", False, f"error: {exc}")
        upload_id = None

    # --- 5. EEG workflow works ---
    analysis = None
    try:
        an = api.handle(ApiRequest(ApiOperation.START_ANALYSIS, {"upload_id": upload_id}, token=token))
        analysis = an.body
        workflow = svc.get_workflow(an.body["workflow_id"])
        ok = (an.status == ResponseStatus.CREATED and workflow.status == WorkflowStatus.COMPLETED
              and workflow.stages == tuple(WorkflowStage))
        check("5. EEG workflow works", ok,
              f"status={workflow.status.value} stages={len(workflow.stages)}")
    except Exception as exc:
        check("5. EEG workflow works", False, f"error: {exc}")

    # --- 6. APIs work ---
    try:
        aid = analysis["analysis_id"]
        pred = api.handle(ApiRequest(ApiOperation.RETRIEVE_PREDICTION, {"analysis_id": aid}, token=token))
        conf = api.handle(ApiRequest(ApiOperation.RETRIEVE_CONFIDENCE, {"analysis_id": aid}, token=token))
        expl = api.handle(ApiRequest(ApiOperation.RETRIEVE_EXPLANATION, {"analysis_id": aid}, token=token))
        hist = api.handle(ApiRequest(ApiOperation.LIST_ANALYSIS_HISTORY, {}, token=token))
        unauth = api.handle(ApiRequest(ApiOperation.LIST_EEG, {}))  # no token
        ok = (api.version == "v1" and pred.ok and conf.ok and expl.ok and hist.ok
              and unauth.status == ResponseStatus.UNAUTHORIZED
              and set(api.api_record.operations) == set(ApiOperation))
        check("6. APIs work", ok, f"version={api.version} n_ops={len(api.api_record.operations)}")
    except Exception as exc:
        check("6. APIs work", False, f"error: {exc}")

    # --- 7. validation works ---
    try:
        report = svc.integrity(analysis["workflow_id"])
        ok = report.ok and report.to_dict()["n_checks"] == 8
        check("7. Validation works", ok,
              f"integrity_ok={report.ok} n_checks={report.to_dict()['n_checks']}")
    except Exception as exc:
        check("7. Validation works", False, f"error: {exc}")

    # --- 8. registry works ---
    try:
        counts = svc.registry.counts()
        present = all(counts[k.value] >= 1 for k in (
            EntityKind.USER, EntityKind.SESSION, EntityKind.UPLOAD, EntityKind.REQUEST,
            EntityKind.RESPONSE, EntityKind.WORKFLOW, EntityKind.ANALYSIS, EntityKind.API))
        ok = present and svc.registry.orphans() == []
        check("8. Registry works", ok,
              f"n_records={len(svc.registry.list_ids())} orphans={len(svc.registry.orphans())}")
    except Exception as exc:
        check("8. Registry works", False, f"error: {exc}")

    # --- 9. audit integration works ---
    try:
        wf = svc.get_workflow(analysis["workflow_id"])
        log = svc.workflow_service.audit_log_for(wf.workflow_id)
        kinds = {ev.kind for ev in log.events()}
        ok = (log.verify() and wf.audit_head == log.head
              and {"workflow_started", "prediction_generated", "workflow_completed"} <= kinds)
        check("9. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("9. Audit integration works", False, f"error: {exc}")

    # --- 10. lineage integration works ---
    try:
        wf = svc.get_workflow(analysis["workflow_id"])
        kinds = {n.kind for n in svc.lineage.chain(wf.lineage_id)}
        ok = svc.lineage.verify_chain(wf.lineage_id) and {
            "user", "upload", "eeg", "processed_eeg", "feature", "model", "prediction",
            "case", "patient"} <= kinds
        check("10. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("10. Lineage integration works", False, f"error: {exc}")

    # --- 11. reports generate ---
    try:
        reports = svc.reports(analysis["workflow_id"])
        expected = {"user_report", "workflow_report", "analysis_report", "api_report",
                    "registry_report", "audit_report", "lineage_report", "validation_report"}
        ok = (set(reports) == expected and reports == svc.reports(analysis["workflow_id"])
              and reports["validation_report"]["ok"] is True)
        check("11. Reports generate", ok, f"reports={len(reports)}")
    except Exception as exc:
        check("11. Reports generate", False, f"error: {exc}")

    # --- 14. determinism preserved ---
    try:
        def run(sub):
            s = ApplicationBackendService(workspace_dir=str(pathlib.Path(tmp) / sub),
                                          entropy=DeterministicEntropy("det"))
            s.prepare_model(cohort, architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7)
            s.do_register(username="d", password="password123", roles=["clinician"])
            tok = s.auth.login(username="d", password="password123").token
            with open(fixtures[fx.VALID_EDF], "rb") as fh:
                c = fh.read()
            uid = s.api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                          {"filename": "r.edf", "content": c}, token=tok)).body["upload_id"]
            res = s.api.handle(ApiRequest(ApiOperation.START_ANALYSIS,
                                          {"upload_id": uid}, token=tok)).body
            return res["prediction_id"], s.get_workflow(res["workflow_id"]).version.version
        a = run("det_a")
        b = run("det_b")
        check("14. Determinism preserved", a == b, "re-run reproduces prediction id + workflow version")
    except Exception as exc:
        check("14. Determinism preserved", False, f"error: {exc}")

    # --- 15. workflow traceability preserved ---
    try:
        wf = svc.get_workflow(analysis["workflow_id"])
        node = svc.lineage.get(wf.lineage_id)
        asset = svc.workflow_service.inference_asset_for(wf.prediction_id)
        upload_node = svc.get_upload(wf.upload_id).lineage_id
        ok = (asset.lineage_id in node.parents and upload_node in node.parents
              and svc.lineage.verify_chain(wf.lineage_id))
        check("15. Workflow traceability preserved", ok, "workflow -> upload + prediction")
    except Exception as exc:
        check("15. Workflow traceability preserved", False, f"error: {exc}")

    # --- 12. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_application_backend.py", "tests/test_application_backend_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("12. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("12. Tests pass", False, f"error: {exc}")

    # --- 13. repository boundaries preserved ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_boundaries.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("13. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("13. Repository boundaries preserved", False, f"error: {exc}")

    # --- report (ordered 1..15) ---
    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nPRODUCTIZATION P6 — APPLICATION BACKEND PLATFORM — FINAL VALIDATION")
    print("=" * 68)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 68)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
