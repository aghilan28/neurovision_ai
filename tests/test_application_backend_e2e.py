"""End-to-end test for Productization P6 — Application Backend Platform.

Demonstrates the full required deliverable through application backend services only:

    a user authenticates -> uploads a real EEG file -> triggers analysis ->
    a prediction + confidence + explanation are generated -> the user retrieves results

and that the whole thing is traceable (User -> Upload -> EEG -> Processed -> Feature ->
Model -> Prediction), audited, registered, validated, and deterministic — built on the
real P1-P5 services and the committed EEG fixtures (no replacement systems).
"""

from __future__ import annotations

from backend.model_foundation import ModelArchitecture
from backend.application_backend import (
    ApplicationBackendService, ApiRequest, ApiOperation, ResponseStatus, DeterministicEntropy,
)
import _eeg_fixtures as fx

FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _cohort_files(eeg_fixtures):
    return [(f"P-{i}", f"C-{i}", eeg_fixtures[name]) for i, name in enumerate(FIXTURES)]


def _run_full_flow(service: ApplicationBackendService, eeg_fixtures, *, username="dr.who",
                   password="time-lord-1"):
    service.prepare_model(_cohort_files(eeg_fixtures), architecture=ModelArchitecture.EEGNET,
                          dataset_key="cohort", seed=7)
    api = service.api
    reg = api.handle(ApiRequest(ApiOperation.REGISTER_USER,
                                {"username": username, "password": password, "roles": ["clinician"]}))
    assert reg.status == ResponseStatus.CREATED
    token = api.handle(ApiRequest(ApiOperation.LOGIN,
                                  {"username": username, "password": password})).body["token"]
    with open(eeg_fixtures[fx.VALID_EDF], "rb") as fh:
        content = fh.read()
    upload = api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                   {"filename": "icu_recording.edf", "content": content}, token=token))
    assert upload.status == ResponseStatus.CREATED
    analysis = api.handle(ApiRequest(ApiOperation.START_ANALYSIS,
                                     {"upload_id": upload.body["upload_id"]}, token=token))
    assert analysis.status == ResponseStatus.CREATED
    return api, token, analysis.body


def test_full_application_deliverable(eeg_fixtures, tmp_path):
    service = ApplicationBackendService(workspace_dir=str(tmp_path / "ws"),
                                        entropy=DeterministicEntropy("e2e"))
    api, token, result = _run_full_flow(service, eeg_fixtures)

    # the analysis surfaced a prediction + confidence + calibration band
    assert result["confidence_level"] in {"very_low", "low", "moderate", "high"}
    assert result["calibration_quality"] in {
        "well_calibrated", "moderately_calibrated", "poorly_calibrated"}

    aid = result["analysis_id"]
    prediction = api.handle(ApiRequest(ApiOperation.RETRIEVE_PREDICTION,
                                       {"analysis_id": aid}, token=token)).body["prediction"]
    confidence = api.handle(ApiRequest(ApiOperation.RETRIEVE_CONFIDENCE,
                                       {"analysis_id": aid}, token=token)).body["confidence"]
    explanation = api.handle(ApiRequest(ApiOperation.RETRIEVE_EXPLANATION,
                                        {"analysis_id": aid}, token=token)).body["explanation"]
    # uncertainty is always reported alongside the label (NR-4)
    assert abs(sum(c["probability"] for c in prediction["classes"]) - 1.0) < 1e-6
    assert "confidence_level" in confidence
    assert len(explanation["feature_contributions"]) == 29

    # the whole workflow is integrity-validated, registered, audited, and traceable
    report = service.integrity(result["workflow_id"])
    assert report.ok and report.to_dict()["n_checks"] == 8
    workflow = service.get_workflow(result["workflow_id"])
    assert service.lineage.verify_chain(workflow.lineage_id)
    assert {"user", "upload", "eeg", "processed_eeg", "feature", "model", "prediction",
            "case", "patient"} <= {n.kind for n in service.lineage.chain(workflow.lineage_id)}
    assert service.registry.orphans() == []


def test_history_lists_the_users_analysis(eeg_fixtures, tmp_path):
    service = ApplicationBackendService(workspace_dir=str(tmp_path / "ws"),
                                        entropy=DeterministicEntropy("hist"))
    api, token, result = _run_full_flow(service, eeg_fixtures)
    history = api.handle(ApiRequest(ApiOperation.LIST_ANALYSIS_HISTORY, {}, token=token))
    assert history.ok
    assert any(a["analysis_id"] == result["analysis_id"] for a in history.body["analyses"])


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    """Two independent services reproduce the same prediction id + workflow version."""
    def run(sub):
        service = ApplicationBackendService(workspace_dir=str(tmp_path / sub),
                                            entropy=DeterministicEntropy("det"))
        _, _, result = _run_full_flow(service, eeg_fixtures, username="dr.det",
                                      password="determinism-1")
        workflow = service.get_workflow(result["workflow_id"])
        return result["prediction_id"], workflow.version.version

    a = run("a")
    b = run("b")
    assert a == b
