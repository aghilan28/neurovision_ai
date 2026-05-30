"""End-to-end test for Productization P7 — Application Frontend Platform.

Demonstrates the full required deliverable through a real frontend interface driving the
real backend:

    log in -> upload EEG -> run analysis -> receive prediction -> view confidence ->
    view explanation -> access reports

plus cross-run determinism of the rendered product, and the NR-8 boundary (the frontend
imports no domain module).
"""

from __future__ import annotations

from backend.application_backend import DeterministicEntropy
from frontend.application_frontend import FrontendValidator, ALL_OPERATIONS, reporting
from scripts.application_frontend_gateway import build_live_app

FIXTURES = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
            "valid_raw.fif", "valid.set"]


def _cohort(eeg_fixtures):
    return [(f"P-{i}", f"C-{i}", eeg_fixtures[n]) for i, n in enumerate(FIXTURES)]


def _run_journey(eeg_fixtures, workspace, *, seed_label="e2e"):
    svc, gateway, app = build_live_app(_cohort(eeg_fixtures), workspace_dir=str(workspace),
                                       entropy=DeterministicEntropy(seed_label))
    assert app.register("dr.frontend", "password123", "password123", "clinician").ok
    assert app.login("dr.frontend", "password123").ok
    app.dashboard()
    with open(eeg_fixtures["valid.edf"], "rb") as fh:
        content = fh.read()
    upload_id = app.upload("icu_recording.edf", content).data["upload"]["upload_id"]
    analysis = app.start_analysis(upload_id)
    return svc, gateway, app, analysis.data["workflow"]["analysis_id"]


def test_full_frontend_deliverable(eeg_fixtures, tmp_path):
    svc, gateway, app, analysis_id = _run_journey(eeg_fixtures, tmp_path / "ws")

    # the user receives a prediction with confidence + explanation (NR-4)
    prediction_html = app.render_prediction(analysis_id)
    assert "Prediction" in prediction_html and "Uncertainty (always shown)" in prediction_html
    prediction = app.state.predictions[analysis_id]
    assert prediction.confidence_level and prediction.calibration_quality
    assert len(prediction.explanation.get("feature_contributions", [])) == 29

    # the user can access reports
    reports_html = app.render_reports(analysis_id)
    assert "Available reports" in reports_html
    assert {"prediction_report", "lineage_report"} <= {r.name for r in app.state.reports[analysis_id]}

    # the whole journey is frontend-validated and exercised the core API surface
    report = FrontendValidator().validate(app, analysis_id=analysis_id)
    assert report.ok and report.n_checks == 8
    assert {"register_user", "login", "upload_eeg", "start_analysis", "retrieve_prediction",
            "retrieve_confidence", "retrieve_explanation", "list_reports"} <= set(gateway.call_log)


def test_full_api_surface_exercised(eeg_fixtures, tmp_path):
    """A single journey can exercise every one of the 12 backend operations."""
    svc, gateway, app, analysis_id = _run_journey(eeg_fixtures, tmp_path / "ws")
    upload_id = app.state.uploads[-1].upload_id
    app.view_upload(upload_id)          # retrieve_eeg
    app.refresh_uploads()               # list_eeg
    app.refresh_analyses()              # list_analysis_history
    app.logout()                        # logout
    integration = reporting.build_frontend_integration_report(app.state, gateway.call_log)
    assert integration["all_exercised"]
    assert set(gateway.call_log) >= set(ALL_OPERATIONS)


def test_rendered_product_is_deterministic(eeg_fixtures, tmp_path):
    """Two independent runs render byte-identical pages (determinism preserved)."""
    _, _, app_a, aid_a = _run_journey(eeg_fixtures, tmp_path / "a", seed_label="det")
    _, _, app_b, aid_b = _run_journey(eeg_fixtures, tmp_path / "b", seed_label="det")
    assert aid_a == aid_b
    assert app_a.render_prediction(aid_a) == app_b.render_prediction(aid_b)
    assert app_a.render_reports(aid_a) == app_b.render_reports(aid_b)
    assert app_a.state.signature() == app_b.state.signature()


def test_user_cannot_act_without_login(eeg_fixtures, tmp_path):
    _, _, app, _ = _run_journey(eeg_fixtures, tmp_path / "ws")
    app.logout()
    # a protected action after logout is rejected and routes back to login
    res = app.start_analysis("upload+deadbeefdeadbeef")
    assert res.page == "login" and not app.is_authenticated
