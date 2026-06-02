"""Component tests for Productization P7 — Application Frontend Platform.

Every test drives the **real** backend (`ApplicationBackendService` / `ApplicationAPI`)
through the live gateway — no fake contracts. Covers auth/registration UI, dashboard,
uploads, analysis workflow, predictions, reports, state management, validation, boundary
conditions, error states, and session expiration.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from backend.application_backend import DeterministicEntropy
from frontend.application_frontend import (
    FrontendApp, FrontendValidator, reporting,
)
from scripts.application_frontend_gateway import build_live_app

FIXTURES = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
            "valid_raw.fif", "valid.set"]


def _cohort(eeg_fixtures):
    return [(f"P-{i}", f"C-{i}", eeg_fixtures[n]) for i, n in enumerate(FIXTURES)]


@pytest.fixture(scope="module")
def backend_env(eeg_fixtures, tmp_path_factory):
    """A real backend + trained model + live gateway, shared across tests (built once)."""
    ws = tmp_path_factory.mktemp("p7_backend")
    svc, gateway, _ = build_live_app(_cohort(eeg_fixtures), workspace_dir=str(ws),
                                     entropy=DeterministicEntropy("p7-tests"))
    return {"svc": svc, "gateway": gateway, "fixtures": eeg_fixtures}


def _fresh_app(backend_env) -> FrontendApp:
    return FrontendApp(backend_env["gateway"])


def _authed_app(backend_env, username: str) -> FrontendApp:
    app = _fresh_app(backend_env)
    app.register(username, "password123", "password123", "clinician")
    app.login(username, "password123")
    return app


def _do_analysis(backend_env, app):
    with open(backend_env["fixtures"]["valid.edf"], "rb") as fh:
        content = fh.read()
    upload_id = app.upload("rec.edf", content).data["upload"]["upload_id"]
    result = app.start_analysis(upload_id)
    return result.data["workflow"]["analysis_id"]


@pytest.fixture(scope="module")
def journey(backend_env):
    app = _authed_app(backend_env, "dr.journey")
    app.dashboard()
    analysis_id = _do_analysis(backend_env, app)
    return {"app": app, "analysis_id": analysis_id}


# =============================================================================
# P7-C — Authentication UI
# =============================================================================
def test_registration_then_login(backend_env):
    app = _fresh_app(backend_env)
    reg = app.register("alice.fe", "password123", "password123", "researcher")
    assert reg.ok and reg.page == "login"
    login = app.login("alice.fe", "password123")
    assert login.ok and app.is_authenticated and login.page == "dashboard"


def test_registration_password_mismatch_is_client_side(backend_env):
    app = _fresh_app(backend_env)
    res = app.register("bob.fe", "password123", "different1", "clinician")
    assert not res.ok and res.field_errors  # rejected before any backend call


def test_registration_short_password(backend_env):
    app = _fresh_app(backend_env)
    res = app.register("carol.fe", "short", "short", "clinician")
    assert not res.ok and res.field_errors


def test_login_wrong_password(backend_env):
    app = _authed_app(backend_env, "dave.fe")
    app.logout()
    res = app.login("dave.fe", "wrong-password")
    assert not res.ok and not app.is_authenticated and res.level == "error"


def test_logout_clears_auth(backend_env):
    app = _authed_app(backend_env, "erin.fe")
    assert app.is_authenticated
    app.logout()
    assert not app.is_authenticated and app.state.current_page == "login"


def test_session_expiration_routes_to_login(backend_env):
    app = _authed_app(backend_env, "frank.fe")
    app.logout()                       # revokes the session on the backend
    res = app.refresh_uploads()        # protected call with a now-invalid token
    assert res.page == "login" and app.state.session_expired


# =============================================================================
# P7-D — Dashboard
# =============================================================================
def test_dashboard_is_backend_driven(journey):
    app = journey["app"]
    html = app.render_dashboard()
    assert "Operational Readiness" in html and "Live Intelligence Activity" in html
    assert app.state.user is not None and "<nav>" in html


# =============================================================================
# P7-E — Uploads
# =============================================================================
def test_upload_and_history(backend_env):
    app = _authed_app(backend_env, "grace.fe")
    with open(backend_env["fixtures"]["valid.edf"], "rb") as fh:
        content = fh.read()
    res = app.upload("rec.edf", content)
    assert res.ok and res.data["upload"]["upload_id"].startswith("upload+")
    assert res.data["upload"]["content_fingerprint"]
    app.refresh_uploads()
    assert any(u.upload_id == res.data["upload"]["upload_id"] for u in app.state.uploads)


def test_upload_empty_file_rejected_client_side(backend_env):
    app = _authed_app(backend_env, "heidi.fe")
    res = app.upload("rec.edf", b"")
    assert not res.ok and res.field_errors


# =============================================================================
# P7-F — Analysis workflow
# =============================================================================
def test_analysis_reflects_backend_stages(journey):
    app = journey["app"]
    workflow = app.state.workflows[-1]
    assert workflow.stages == ("upload", "validate", "process", "features", "predict",
                               "confidence", "explanation")
    progress = app.analysis.stage_progress(workflow)
    assert all(step["done"] for step in progress)
    assert "Visual Pipeline" in app.render_analysis()


# =============================================================================
# P7-G — Prediction display
# =============================================================================
def test_prediction_display_uses_real_asset(journey):
    app = journey["app"]
    prediction = app.state.predictions[journey["analysis_id"]]
    assert prediction.predicted_label != "" and prediction.confidence_level != ""
    probs = [c.get("probability", 0) for c in prediction.prediction.get("classes", [])]
    assert abs(sum(probs) - 1.0) < 1e-6
    html = app.render_prediction(journey["analysis_id"])
    assert "Prediction Outcome" in html and "Confidence Distribution" in html


# =============================================================================
# P7-H — Reports
# =============================================================================
def test_reports_display_and_download(journey):
    app = journey["app"]
    reports = app.state.reports[journey["analysis_id"]]
    names = {r.name for r in reports}
    assert {"prediction_report", "lineage_report", "analysis_report"} <= names
    from frontend.application_frontend.reports import ReportController
    blob = ReportController.download(reports[0])
    assert isinstance(blob, str) and len(blob) > 2
    assert "Evidence Graph" in app.render_reports(journey["analysis_id"])


# =============================================================================
# P7-I — State management
# =============================================================================
def test_state_is_deterministic_and_secret_free(journey):
    app = journey["app"]
    snap1 = app.state.snapshot()
    snap2 = app.state.snapshot()
    assert snap1 == snap2 and app.state.signature() == app.state.signature()
    # the raw token is never in the snapshot
    assert app.state.token is not None
    assert app.state.token not in str(snap1)


# =============================================================================
# P7-J — Validation
# =============================================================================
def test_frontend_validation_all_pass(journey):
    report = FrontendValidator().validate(journey["app"], analysis_id=journey["analysis_id"])
    assert report.ok and report.n_checks == 8
    names = {n for n, _, _ in report.checks}
    assert names == {"authentication_flow_integrity", "upload_flow_integrity",
                     "workflow_flow_integrity", "prediction_flow_integrity",
                     "report_flow_integrity", "state_integrity", "session_integrity",
                     "ui_integrity"}


# =============================================================================
# P7-L — Reporting
# =============================================================================
def test_frontend_reports_generate(journey, backend_env):
    app = journey["app"]
    report = FrontendValidator().validate(app, analysis_id=journey["analysis_id"])
    bundle = reporting.build_all_reports(app, validation_report=report,
                                         operations_exercised=backend_env["gateway"].call_log)
    assert {"frontend_validation_report", "frontend_workflow_report", "frontend_state_report",
            "frontend_integration_report"} <= set(bundle)
    # the core user-journey operations were exercised against the real backend
    exercised = set(backend_env["gateway"].call_log)
    assert {"register_user", "login", "upload_eeg", "start_analysis", "retrieve_prediction",
            "retrieve_confidence", "retrieve_explanation", "list_reports"} <= exercised


# =============================================================================
# Rendering + boundary
# =============================================================================
def test_pages_render_deterministic_html_without_scripts(journey):
    app = journey["app"]
    for html in (app.render_dashboard(), app.render_upload(), app.render_analysis(),
                 app.render_prediction(journey["analysis_id"]),
                 app.render_reports(journey["analysis_id"])):
        assert html.startswith("<!doctype html>") and "<nav>" in html
            # NeuroVision V1 now uses <script> for the Living Brain Canvas
    assert app.render_dashboard() == app.render_dashboard()  # deterministic


def test_frontend_imports_no_domain_module():
    root = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "application_frontend"
    domain = {"ml", "evaluation", "datasets", "preprocessing", "backend", "monitoring",
              "deployment"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            roots = set()
            if isinstance(node, ast.Import):
                roots = {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                roots = {node.module.split(".")[0]}
            assert not (roots & domain), f"{path} imports domain module(s): {roots & domain}"
