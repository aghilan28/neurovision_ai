"""Final validation for Productization P7 — Application Frontend Platform.

Objectively verifies the directive's 15 phase-completion criteria: that a user can log
in, upload an EEG, run an analysis, receive a prediction, view its confidence +
explanation, and access reports through a **real frontend** that consumes the **real**
backend API — with deterministic state, frontend validation, the test suite green, the
NR-8 boundary intact, and no duplicated business logic.

    python -m scripts.verify_productization_p7
"""

from __future__ import annotations

import ast
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
    from backend.application_backend import DeterministicEntropy
    from frontend.application_frontend import FrontendValidator, ALL_OPERATIONS
    from scripts.application_frontend_gateway import build_live_app

    tmp = tempfile.mkdtemp(prefix="nv_p7_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))
    names = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
             "valid_raw.fif", "valid.set"]
    cohort = [(f"P-{i}", f"C-{i}", fixtures[n]) for i, n in enumerate(names)]

    svc, gateway, app = build_live_app(cohort, workspace_dir=str(pathlib.Path(tmp) / "ws"),
                                       entropy=DeterministicEntropy("verify-p7"))

    # --- 2. registration works ---
    try:
        reg = app.register("dr.verify", "password123", "password123", "clinician")
        bad = app.register("dr.verify2", "password123", "mismatch12", "clinician")
        check("2. Registration works", reg.ok and not bad.ok,
              f"register={reg.ok} mismatch_rejected={not bad.ok}")
    except Exception as exc:
        check("2. Registration works", False, f"error: {exc}")

    # --- 1. login works ---
    try:
        login = app.login("dr.verify", "password123")
        bad_login = app.login("dr.verify", "wrong-password")
        check("1. Login works", login.ok and app.is_authenticated and not bad_login.ok,
              f"login={login.ok} bad_login_rejected={not bad_login.ok}")
        if not app.is_authenticated:                 # bad_login may have left us logged out
            app.login("dr.verify", "password123")
    except Exception as exc:
        check("1. Login works", False, f"error: {exc}")

    # --- 3. sessions work ---
    try:
        token_present = app.state.token is not None
        # a fresh app whose protected call after logout routes to login (expiration)
        probe = app.__class__(gateway)
        probe.register("probe.user", "password123", "password123", "clinician")
        probe.login("probe.user", "password123")
        probe.logout()
        expired = probe.refresh_uploads()
        check("3. Sessions work", token_present and expired.page == "login"
              and probe.state.session_expired,
              f"token_present={token_present} expiration_handled={probe.state.session_expired}")
    except Exception as exc:
        check("3. Sessions work", False, f"error: {exc}")

    # --- 4. dashboard works ---
    try:
        app.dashboard()
        html = app.render_dashboard()
        check("4. Dashboard works", "User summary" in html and "System status" in html
              and "<nav>" in html, "user + system summaries rendered")
    except Exception as exc:
        check("4. Dashboard works", False, f"error: {exc}")

    # --- 5. upload workflow works ---
    upload_id = None
    try:
        with open(fixtures["valid.edf"], "rb") as fh:
            content = fh.read()
        up = app.upload("rec.edf", content)
        upload_id = up.data["upload"]["upload_id"]
        empty = app.upload("rec.edf", b"")
        app.view_upload(upload_id)
        check("5. Upload workflow works", up.ok and bool(upload_id) and not empty.ok,
              f"upload_id={upload_id} empty_rejected={not empty.ok}")
    except Exception as exc:
        check("5. Upload workflow works", False, f"error: {exc}")

    # --- 6. analysis workflow works ---
    analysis_id = None
    try:
        res = app.start_analysis(upload_id)
        analysis_id = res.data["workflow"]["analysis_id"]
        workflow = app.state.workflows[-1]
        check("6. Analysis workflow works", res.ok and workflow.stages == (
            "upload", "validate", "process", "features", "predict", "confidence", "explanation"),
              f"stages={len(workflow.stages)}")
    except Exception as exc:
        check("6. Analysis workflow works", False, f"error: {exc}")

    # --- 7. prediction display works ---
    try:
        html = app.render_prediction(analysis_id)
        pred = app.state.predictions[analysis_id]
        probs = [c.get("probability", 0) for c in pred.prediction.get("classes", [])]
        check("7. Prediction display works",
              "Uncertainty (always shown)" in html and bool(pred.predicted_label)
              and abs(sum(probs) - 1.0) < 1e-6,
              f"label={pred.predicted_label} confidence={pred.confidence_level}")
    except Exception as exc:
        check("7. Prediction display works", False, f"error: {exc}")

    # --- 8. report display works ---
    try:
        html = app.render_reports(analysis_id)
        names_ = {r.name for r in app.state.reports[analysis_id]}
        check("8. Report display works",
              "Available reports" in html and {"prediction_report", "lineage_report"} <= names_,
              f"reports={len(names_)}")
    except Exception as exc:
        check("8. Report display works", False, f"error: {exc}")

    # --- 9. state management works ---
    try:
        snap1, snap2 = app.state.snapshot(), app.state.snapshot()
        secret_free = app.state.token is not None and app.state.token not in str(snap1)
        check("9. State management works", snap1 == snap2 and secret_free,
              f"deterministic={snap1 == snap2} secret_free={secret_free}")
    except Exception as exc:
        check("9. State management works", False, f"error: {exc}")

    # --- 10. validation works ---
    try:
        report = FrontendValidator().validate(app, analysis_id=analysis_id)
        check("10. Validation works", report.ok and report.n_checks == 8,
              f"ok={report.ok} n_checks={report.n_checks}")
    except Exception as exc:
        check("10. Validation works", False, f"error: {exc}")

    # --- 12. backend integration works ---
    try:
        app.refresh_uploads()
        app.refresh_analyses()
        exercised = set(gateway.call_log)
        check("12. Backend integration works", exercised >= set(ALL_OPERATIONS),
              f"operations_exercised={len(exercised)}/12")
    except Exception as exc:
        check("12. Backend integration works", False, f"error: {exc}")

    # --- 14. no duplicated business logic (frontend imports no domain module) ---
    try:
        root = REPO / "frontend" / "application_frontend"
        domain = {"ml", "evaluation", "datasets", "preprocessing", "backend", "monitoring",
                  "deployment"}
        leaks = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                roots = set()
                if isinstance(node, ast.Import):
                    roots = {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    roots = {node.module.split(".")[0]}
                if roots & domain:
                    leaks.append((str(path.relative_to(REPO)), sorted(roots & domain)))
        check("14. No duplicated business logic", not leaks,
              "frontend imports no domain module; all logic via the backend gateway")
    except Exception as exc:
        check("14. No duplicated business logic", False, f"error: {exc}")

    # --- 15. end-to-end user workflow works ---
    try:
        e2e = app.__class__(gateway)
        e2e.register("e2e.user", "password123", "password123", "clinician")
        e2e.login("e2e.user", "password123")
        with open(fixtures["valid_raw.fif"], "rb") as fh:
            c = fh.read()
        uid = e2e.upload("scan.fif", c).data["upload"]["upload_id"]
        ar = e2e.start_analysis(uid)
        aid = ar.data["workflow"]["analysis_id"]
        ok = (e2e.is_authenticated and ar.ok
              and "Uncertainty (always shown)" in e2e.render_prediction(aid)
              and "Available reports" in e2e.render_reports(aid))
        check("15. End-to-end user workflow works", ok,
              "login -> upload -> analyse -> prediction -> confidence -> explanation -> reports")
    except Exception as exc:
        check("15. End-to-end user workflow works", False, f"error: {exc}")

    # --- 11. frontend tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_application_frontend.py", "tests/test_application_frontend_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Frontend tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Frontend tests pass", False, f"error: {exc}")

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
    print("\nPRODUCTIZATION P7 — APPLICATION FRONTEND PLATFORM — FINAL VALIDATION")
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
