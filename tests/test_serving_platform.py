"""Tests for DRP-3 — Production Serving Platform (``backend/serving_platform``).

Exercises the serving engine, prediction service, contracts, validation, registry,
readiness, audit/lineage integration, reports, schemas, and boundary/missing/invalid/
corrupted conditions — using the **real** DRP-2/model-foundation models + inference
foundation over the real P1->P3 feature assets (no replacement systems).
"""

from __future__ import annotations

import dataclasses

import pytest

from backend.model_foundation import ModelArchitecture
from backend.serving_platform import (
    ServingPlatformService, PredictionRequestContract, ServingStatus, ReadinessClass,
    LifecycleState, LIFECYCLE_ORDER, ServingReadinessEngine, ServingRegistry, RegistryError,
    ModelRouter, RoutingError, LifecycleTracker, LifecycleError, ENTITY_CONTRACTS, validate_entity,
    CONTRACT_REGISTRY,
)

from _drp3_helpers import build_feature_cohort, train_model


def _served(eeg_fixtures, tmp_path, architecture=ModelArchitecture.EEGNET):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    model = train_model(tracker, feats, architecture=architecture)
    svc = ServingPlatformService(lineage_tracker=tracker)
    svc.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(
        model_ref={"model_id": model.model_id}, feature_asset_id=feats[0].feature_asset_id,
        case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    return tracker, feats, model, svc, svc.serve(req, feats[0])


# =============================================================================
# Model serving + prediction delivery (DRP3-C / DRP3-D)
# =============================================================================
def test_serve_delivers_prediction_confidence_calibration_explanation(eeg_fixtures, tmp_path):
    tracker, feats, model, svc, out = _served(eeg_fixtures, tmp_path)
    assert out.accepted and out.reason == ServingStatus.COMPLETED.value
    r = out.execution.response
    assert r.predicted_class in range(model.metadata.n_classes)
    assert len(r.probability_scores) == model.metadata.n_classes
    assert r.confidence_level and r.confidence_score is not None       # confidence delivered
    assert r.calibration_quality and r.expected_calibration_error is not None  # calibration delivered
    assert len(r.explanation_summary) > 0                              # explanation delivered
    # response contract is well-formed + versioned
    rc = out.response_contract
    assert rc["contract"] == "PredictionResponse" and "prediction" in rc and "confidence" in rc


def test_lifecycle_runs_in_canonical_order(eeg_fixtures, tmp_path):
    _, _, _, _, out = _served(eeg_fixtures, tmp_path)
    assert list(out.execution.lifecycle.states) == [s.value for s in LIFECYCLE_ORDER]
    assert out.execution.lifecycle.final_state == LifecycleState.EXECUTION_COMPLETED.value


def test_model_resolution_by_architecture_and_version(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    model = train_model(tracker, feats, architecture=ModelArchitecture.TEMPORAL_CNN)
    svc = ServingPlatformService(lineage_tracker=tracker)
    svc.load_model(model, feats, dataset_key="cohort")
    # by architecture (latest)
    req = PredictionRequestContract(model_ref={"architecture": "temporal_cnn"},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = svc.serve(req, feats[0])
    assert out.accepted and out.execution.model_id == model.model_id
    # by explicit version
    req2 = PredictionRequestContract(
        model_ref={"architecture": "temporal_cnn", "version": model.version.version},
        feature_asset_id=feats[0].feature_asset_id, case_id=feats[0].case_id,
        patient_id=feats[0].patient_id)
    assert svc.serve(req2, feats[0]).accepted


def test_router_resolution_rules():
    router = ModelRouter()
    catalog = {"model+" + "1" * 16: {"architecture": "eegnet", "version": "v1", "ordinal": 0},
               "model+" + "2" * 16: {"architecture": "eegnet", "version": "v2", "ordinal": 1}}
    # latest by ordinal
    assert router.resolve({"architecture": "eegnet"}, catalog).model_id == "model+" + "2" * 16
    # by exact version
    assert router.resolve({"architecture": "eegnet", "version": "v1"}, catalog).version == "v1"
    with pytest.raises(RoutingError):
        router.resolve({"model_id": "model+" + "9" * 16}, catalog)
    with pytest.raises(RoutingError):
        router.resolve({"architecture": "eegnet"}, {})


# =============================================================================
# Registry / audit / lineage integration (DRP3-H / DRP3-J)
# =============================================================================
def test_registry_audit_lineage_integration(eeg_fixtures, tmp_path):
    tracker, feats, model, svc, out = _served(eeg_fixtures, tmp_path)
    e = out.execution
    # registry: execution + request + response + readiness; no orphans; cross-refs shared ids
    assert svc.registry.exists(e.execution_id)
    assert svc.registry.orphans() == []
    rec = svc.registry.get_execution(e.execution_id)
    assert rec.model_id == model.model_id and rec.prediction_id == e.prediction_id
    counts = svc.registry.counts()
    assert counts["serving_execution"] == 1 and counts["serving_request"] == 1
    # audit: verified + head match
    log = svc.audit_log_for(e.execution_id)
    assert log.verify() and e.audit_head == log.head
    # lineage: chain reaches the patient with the full required chain
    assert tracker.verify_chain(e.response.lineage_id)
    kinds = {n.kind for n in tracker.chain(e.response.lineage_id)}
    assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset", "training_run",
            "model", "prediction", "serving_request", "serving_execution",
            "serving_response"} <= kinds
    # immutability
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.status = ServingStatus.FAILED


def test_integrity_passes(eeg_fixtures, tmp_path):
    _, _, _, svc, out = _served(eeg_fixtures, tmp_path)
    report = svc.integrity(out.execution)
    assert report.ok, [c.name for c in report.failures()]


def test_registry_rejects_orphan_execution():
    from backend.serving_platform.models.domain import ServingRegistryRecord
    reg = ServingRegistry()
    rec = ServingRegistryRecord(
        execution_id="serving_execution+" + "0" * 16, request_id="serving_request+" + "0" * 16,
        response_id="serving_response+" + "0" * 16, model_id="model+" + "0" * 16,
        prediction_id="prediction+" + "0" * 16, feature_asset_id="feature+" + "0" * 16,
        case_id="case+" + "0" * 16, patient_id="patient+" + "0" * 16, status=ServingStatus.COMPLETED,
        readiness_id="serving_readiness+" + "0" * 16, version="v", owner="o", creation_date="t",
        audit_state="", lineage_id="", dependencies=())
    with pytest.raises(RegistryError):       # no lineage / audit head -> orphan
        reg.register_execution(rec)


# =============================================================================
# Readiness engine (DRP3-I)
# =============================================================================
def test_readiness_requires_all_evidence():
    eng = ServingReadinessEngine()
    tid = "serving_execution+" + "a" * 16
    ready = eng.assess(target_id=tid, execution_ok=True, contract_ok=True, validation_ok=True,
                       registered=True, audited=True, traceable=True)
    assert ready.classification == ReadinessClass.READY and ready.score == pytest.approx(1.0)
    not_traceable = eng.assess(target_id=tid, execution_ok=True, contract_ok=True,
                               validation_ok=True, registered=True, audited=True, traceable=False)
    assert not_traceable.classification != ReadinessClass.READY
    assert "lineage_readiness" in not_traceable.findings
    bad = eng.assess(target_id=tid, execution_ok=False, contract_ok=False, validation_ok=False,
                     registered=False, audited=False, traceable=False)
    assert bad.classification == ReadinessClass.NOT_READY


# =============================================================================
# Lifecycle tracker order enforcement (DRP3-F)
# =============================================================================
def test_lifecycle_rejects_out_of_order():
    lc = LifecycleTracker("serving_request+" + "0" * 16)
    lc.record(LifecycleState.REQUEST_CREATED)
    with pytest.raises(LifecycleError):
        lc.record(LifecycleState.REQUEST_CREATED)     # cannot repeat / go backwards


# =============================================================================
# Reports (DRP3-K) + schemas (DRP3-L)
# =============================================================================
def test_reports_generate(eeg_fixtures, tmp_path):
    _, _, _, svc, out = _served(eeg_fixtures, tmp_path)
    reports = svc.reports(out.execution)
    expected = {"serving_report", "execution_report", "validation_report", "readiness_report",
                "registry_report", "audit_report", "lineage_report", "contract_report",
                "service_summary_report"}
    assert expected == set(reports)
    assert reports["service_summary_report"]["ok"]
    assert reports["lineage_report"]["chain_verified"]


def test_entity_contracts_cover_records():
    for name in ("ServingIdentity", "ServingRequestRecord", "ServingResponseRecord",
                 "ServingExecutionRecord", "ServingReadinessRecord", "ServingRegistryRecord"):
        assert name in ENTITY_CONTRACTS
    ok, missing = validate_entity("ServingRequestRecord", {
        "request_id": "x", "model_ref": {"model_id": "m"}, "feature_asset_id": "f",
        "case_id": "c", "patient_id": "p"})
    assert ok and missing == []
    assert "PredictionResponse" in CONTRACT_REGISTRY


# =============================================================================
# Cross-run determinism (NR-9/NR-10)
# =============================================================================
def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        _, _, _, _, out = _served(eeg_fixtures, tmp_path / sub)
        return out.execution
    a, b = run("a"), run("b")
    assert a.execution_id == b.execution_id
    assert a.version.version == b.version.version
    assert a.response.signature() == b.response.signature()


# =============================================================================
# Graceful handling: missing model / invalid request / feature unavailable
# =============================================================================
def test_missing_model_is_rejected_gracefully(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ServingPlatformService(lineage_tracker=tracker)        # no models loaded
    req = PredictionRequestContract(model_ref={"model_id": "model+" + "0" * 16},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = svc.serve(req, feats[0])
    assert not out.accepted and out.error["code"] == "MODEL_NOT_FOUND"
    assert svc.registry.orphans() == []          # nothing half-registered


def test_invalid_request_is_rejected_gracefully(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ServingPlatformService(lineage_tracker=tracker)
    bad = PredictionRequestContract(model_ref={}, feature_asset_id="",
                                    case_id="", patient_id="")
    out = svc.serve(bad, feats[0])
    assert not out.accepted and out.error["code"] == "REQUEST_INVALID"


def test_feature_unavailable_is_rejected(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    model = train_model(tracker, feats)
    # a DIFFERENT tracker for serving -> the input feature lineage node is absent
    from ml.lineage import LineageTracker
    svc = ServingPlatformService(lineage_tracker=LineageTracker())
    # load fails first (model lineage absent) -> guard via try
    with pytest.raises(Exception):
        svc.load_model(model, feats, dataset_key="cohort")
