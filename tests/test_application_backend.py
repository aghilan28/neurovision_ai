"""Component tests for Productization P6 — Application Backend Platform.

Covers authentication, sessions, users, the EEG workflow orchestration, the versioned
API, request/integrity validation, the registry, audit, lineage, reports, boundary
conditions, security conditions, and determinism — all over the **real** reused P1-P5
services and the committed EEG fixtures (no replacement systems).
"""

from __future__ import annotations

import dataclasses

import pytest

from backend.model_foundation import ModelArchitecture
from backend.application_backend import (
    ApplicationBackendService, ApiRequest, ApiOperation, ResponseStatus, UserRole, UserStatus,
    SessionStatus, WorkflowStatus, WorkflowStage, EntityKind, DeterministicEntropy,
    hash_password, verify_password, token_fingerprint, mint_identity, validate_identity,
    IdentityError,
)
import _eeg_fixtures as fx

FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


# =============================================================================
# Fixtures
# =============================================================================
def _build_service(workspace) -> ApplicationBackendService:
    return ApplicationBackendService(workspace_dir=str(workspace),
                                     entropy=DeterministicEntropy("test-seed"))


def _cohort_files(eeg_fixtures):
    return [(f"P-{i}", f"C-{i}", eeg_fixtures[name]) for i, name in enumerate(FIXTURES)]


@pytest.fixture
def svc(tmp_path) -> ApplicationBackendService:
    """A fresh service (no trained model) for auth/user/validation tests (cheap)."""
    return _build_service(tmp_path / "ws")


@pytest.fixture(scope="module")
def analysis_env(eeg_fixtures, tmp_path_factory):
    """A service with a prepared model + one completed analysis (shared, read-only)."""
    ws = tmp_path_factory.mktemp("p6_analysis")
    service = ApplicationBackendService(workspace_dir=str(ws), entropy=DeterministicEntropy("env"))
    service.prepare_model(_cohort_files(eeg_fixtures), architecture=ModelArchitecture.EEGNET,
                          dataset_key="cohort", seed=7)
    service.do_register(username="dr.house", password="diagnose-1", roles=["clinician"])
    login = service.api.handle(ApiRequest(ApiOperation.LOGIN,
                                          {"username": "dr.house", "password": "diagnose-1"}))
    token = login.body["token"]
    with open(eeg_fixtures[fx.VALID_EDF], "rb") as fh:
        content = fh.read()
    up = service.api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                       {"filename": "rec.edf", "content": content}, token=token))
    an = service.api.handle(ApiRequest(ApiOperation.START_ANALYSIS,
                                       {"upload_id": up.body["upload_id"]}, token=token))
    return {
        "svc": service, "token": token, "upload_id": up.body["upload_id"],
        "analysis_id": an.body["analysis_id"], "workflow_id": an.body["workflow_id"],
        "prediction_id": an.body["prediction_id"], "user_id": login.body["user_id"],
    }


# =============================================================================
# P6-C — Authentication
# =============================================================================
def test_password_hashing_is_salted_and_verifiable():
    salt = b"0123456789abcdef"
    digest = hash_password("correct horse battery", salt)
    assert verify_password("correct horse battery", salt.hex(), digest)
    assert not verify_password("wrong password", salt.hex(), digest)
    # a different salt yields a different hash for the same password
    assert hash_password("correct horse battery", b"different-salt!!") != digest


def test_register_login_validate_revoke(svc):
    user = svc.do_register(username="alice", password="password123", roles=["researcher"])
    assert user.status == UserStatus.ACTIVE and UserRole.RESEARCHER in user.roles
    result = svc.auth.login(username="alice", password="password123")
    assert result.token and result.session.status == SessionStatus.ACTIVE
    assert svc.auth.validate_session(result.token) is not None
    svc.auth.revoke_session(token=result.token)
    assert svc.auth.validate_session(result.token) is None


def test_duplicate_username_rejected(svc):
    svc.do_register(username="bob", password="password123")
    with pytest.raises(Exception):
        svc.do_register(username="bob", password="password123")


def test_login_with_wrong_password_fails(svc):
    svc.do_register(username="carol", password="password123")
    with pytest.raises(Exception):
        svc.auth.login(username="carol", password="not-the-password")


def test_short_password_rejected(svc):
    with pytest.raises(Exception):
        svc.do_register(username="dave", password="short")


def test_session_stores_only_token_fingerprint(svc):
    svc.do_register(username="erin", password="password123")
    result = svc.auth.login(username="erin", password="password123")
    # the raw token must never be stored on the record
    assert result.token not in str(result.session.to_dict())
    assert result.session.token_fingerprint == token_fingerprint(result.token)


# =============================================================================
# P6-D — User management
# =============================================================================
def test_user_lifecycle_update_status_deactivate(svc):
    user = svc.users.create_user(username="frank", roles=[UserRole.VIEWER])
    updated = svc.users.update_user(user.user_id, roles=[UserRole.CLINICIAN],
                                    metadata={"dept": "neuro"})
    assert UserRole.CLINICIAN in updated.roles and updated.metadata["dept"] == "neuro"
    assert updated.version.version != user.version.version  # chained version bump
    deactivated = svc.users.deactivate_user(user.user_id)
    assert deactivated.status == UserStatus.DEACTIVATED
    with pytest.raises(Exception):
        svc.users.update_user(user.user_id, roles=[UserRole.ADMIN])


def test_user_list_and_audit_history_and_lineage(svc):
    a = svc.users.create_user(username="grace")
    svc.users.create_user(username="heidi")
    ids = {u.user_id for u in svc.users.list_users()}
    assert a.user_id in ids
    log = svc.users.audit_log_for(a.user_id)
    assert log.verify() and a.audit_head == log.head
    kinds = {ev.kind for ev in log.events()}
    assert {"user_created", "user_version_changed"} <= kinds
    assert svc.lineage.exists(a.lineage_id)


def test_user_record_carries_no_secret_material(svc):
    svc.do_register(username="ivan", password="password123")
    user = svc.users.get_by_username("ivan")
    serialized = str(user.to_dict())
    assert "password" not in serialized and "salt" not in serialized and "hash_hex" not in serialized


# =============================================================================
# P6-B — Identity
# =============================================================================
def test_identity_minting_and_validation():
    uid = mint_identity("user", {"username": "zoe"}).id
    assert validate_identity(uid, "user")[0]
    # session derives from a valid user id
    sid = mint_identity("session", {"user_id": uid, "session_key": "abcd"}).id
    assert validate_identity(sid, "session")[0]
    # upstream kinds are referenced-only (never minted here)
    with pytest.raises(IdentityError):
        mint_identity("prediction", {})


# =============================================================================
# P6-E — EEG workflow orchestration
# =============================================================================
def test_workflow_completed_with_full_ordered_stages(analysis_env):
    svc = analysis_env["svc"]
    workflow = svc.get_workflow(analysis_env["workflow_id"])
    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.stages == (
        WorkflowStage.UPLOAD, WorkflowStage.VALIDATE, WorkflowStage.PROCESS,
        WorkflowStage.FEATURES, WorkflowStage.PREDICT, WorkflowStage.CONFIDENCE,
        WorkflowStage.EXPLANATION)
    # the workflow references real reused P1-P5 artifacts
    assert validate_identity(workflow.eeg_asset_id, "eeg")[0]
    assert validate_identity(workflow.processed_id, "signal")[0]
    assert validate_identity(workflow.feature_asset_id, "feature")[0]
    assert validate_identity(workflow.model_id, "model")[0]
    assert validate_identity(workflow.prediction_id, "prediction")[0]


def test_workflow_audit_chain_and_head(analysis_env):
    svc = analysis_env["svc"]
    workflow = svc.get_workflow(analysis_env["workflow_id"])
    log = svc.workflow_service.audit_log_for(workflow.workflow_id)
    assert log.verify() and workflow.audit_head == log.head
    kinds = {ev.kind for ev in log.events()}
    assert {"workflow_started", "eeg_validated", "eeg_processed", "features_generated",
            "prediction_generated", "confidence_generated", "explanation_generated",
            "workflow_completed"} <= kinds


# =============================================================================
# P6-F — API layer
# =============================================================================
def test_full_api_surface_operations(analysis_env):
    svc, token = analysis_env["svc"], analysis_env["token"]
    aid = analysis_env["analysis_id"]
    for op in (ApiOperation.RETRIEVE_PREDICTION, ApiOperation.RETRIEVE_CONFIDENCE,
               ApiOperation.RETRIEVE_EXPLANATION):
        resp = svc.api.handle(ApiRequest(op, {"analysis_id": aid}, token=token))
        assert resp.status == ResponseStatus.OK
    assert svc.api.handle(ApiRequest(ApiOperation.LIST_EEG, {}, token=token)).ok
    assert svc.api.handle(ApiRequest(ApiOperation.LIST_ANALYSIS_HISTORY, {}, token=token)).ok
    reports = svc.api.handle(ApiRequest(ApiOperation.LIST_REPORTS, {"analysis_id": aid}, token=token))
    assert reports.ok and "prediction_report" in reports.body["report_names"]


def test_api_is_versioned(analysis_env):
    svc = analysis_env["svc"]
    assert svc.api.version == "v1"
    assert set(svc.api.api_record.operations) == set(ApiOperation)


def test_unauthenticated_request_is_rejected(analysis_env):
    svc = analysis_env["svc"]
    resp = svc.api.handle(ApiRequest(ApiOperation.LIST_EEG, {}))  # no token
    assert resp.status == ResponseStatus.UNAUTHORIZED


def test_missing_params_is_bad_request(svc):
    resp = svc.api.handle(ApiRequest(ApiOperation.LOGIN, {"username": "x"}))  # no password
    assert resp.status == ResponseStatus.BAD_REQUEST


def test_viewer_cannot_upload_or_analyze(svc):
    svc.do_register(username="vic.viewer", password="password123", roles=["viewer"])
    token = svc.auth.login(username="vic.viewer", password="password123").token
    resp = svc.api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                     {"filename": "x.edf", "content": b"abc"}, token=token))
    assert resp.status == ResponseStatus.FORBIDDEN


def test_cross_user_retrieve_is_not_found(analysis_env, eeg_fixtures):
    svc = analysis_env["svc"]
    svc.do_register(username="mallory", password="password123", roles=["clinician"])
    other_token = svc.auth.login(username="mallory", password="password123").token
    resp = svc.api.handle(ApiRequest(ApiOperation.RETRIEVE_PREDICTION,
                                     {"analysis_id": analysis_env["analysis_id"]}, token=other_token))
    assert resp.status == ResponseStatus.NOT_FOUND


# =============================================================================
# P6-G / P6-K — Validation
# =============================================================================
def test_application_integrity_all_checks_pass(analysis_env):
    svc = analysis_env["svc"]
    report = svc.integrity(analysis_env["workflow_id"])
    assert report.ok and report.to_dict()["n_checks"] == 8
    names = {c.name for c in report.checks}
    assert names == {"authentication_integrity", "session_integrity", "workflow_integrity",
                     "api_integrity", "registry_integrity", "audit_integrity",
                     "lineage_integrity", "version_integrity"}


# =============================================================================
# P6-I — Registry (no orphans)
# =============================================================================
def test_registry_tracks_all_kinds_without_orphans(analysis_env):
    svc = analysis_env["svc"]
    counts = svc.registry.counts()
    for kind in (EntityKind.USER, EntityKind.SESSION, EntityKind.UPLOAD, EntityKind.REQUEST,
                 EntityKind.RESPONSE, EntityKind.WORKFLOW, EntityKind.ANALYSIS, EntityKind.API):
        assert counts[kind.value] >= 1, kind
    assert svc.registry.orphans() == []


# =============================================================================
# P6-J — Lineage (the required chain)
# =============================================================================
def test_workflow_lineage_realizes_full_chain(analysis_env):
    svc = analysis_env["svc"]
    workflow = svc.get_workflow(analysis_env["workflow_id"])
    assert svc.lineage.verify_chain(workflow.lineage_id)
    kinds = {n.kind for n in svc.lineage.chain(workflow.lineage_id)}
    assert {"user", "upload", "eeg", "processed_eeg", "feature", "model", "prediction"} <= kinds
    assert {"case", "patient"} <= kinds  # P1-P5 chain preserved intact


# =============================================================================
# P6-L — Reports (deterministic)
# =============================================================================
def test_reports_are_complete_and_deterministic(analysis_env):
    svc = analysis_env["svc"]
    reports = svc.reports(analysis_env["workflow_id"])
    assert set(reports) == {"user_report", "workflow_report", "analysis_report", "api_report",
                            "registry_report", "audit_report", "lineage_report", "validation_report"}
    assert reports == svc.reports(analysis_env["workflow_id"])  # reproducible
    assert reports["validation_report"]["ok"] is True


# =============================================================================
# Security + boundary
# =============================================================================
def test_records_are_immutable(analysis_env):
    svc = analysis_env["svc"]
    workflow = svc.get_workflow(analysis_env["workflow_id"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        workflow.status = WorkflowStatus.FAILED


def test_backend_application_imports_no_frontend():
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "backend" / "application_backend"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not a.name.startswith("frontend") for a in node.names), path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("frontend"), path
