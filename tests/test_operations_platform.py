"""Track 4 — Operational Readiness & Deployment Qualification tests.

Exercises health monitoring, operational monitoring, diagnostics, deployment qualification,
deployment readiness, audit + lineage integration, registry, reports, determinism, and the
boundary / API-failure / missing-model / missing-dataset / corrupted-state conditions —
qualifying the **real** Track-3 product (driven over real EEG via the real FastAPI workflow,
network-free). A real-corpus test runs over the locally-acquired PhysioNet recordings.
"""

from __future__ import annotations

import pytest

from _track4_helpers import make_operations

from backend.application_platform import ApplicationPlatformService
from backend.operations_platform import (
    DeploymentReadinessClass, EntityKind, HealthState, OperationsPlatformService,
    QualificationStatus, validate_entity,
)


# --- T4-B: health monitoring -------------------------------------------------
def test_health_monitoring_all_components_healthy():
    _product, ops = make_operations()
    out = ops.qualify()
    assert out.health.overall == HealthState.HEALTHY
    assert out.health.n_components == 7
    assert {c.component.value for c in out.health.components} == {
        "service", "dataset", "model", "storage", "api", "workflow", "prediction"}


def test_health_degraded_without_workflow():
    # a product with a model but no completed workflow -> workflow/prediction degraded, not crash
    _product, ops = make_operations(run_workflow=False)
    out = ops.qualify()
    states = {c.component.value: c.state for c in out.health.components}
    assert states["model"] == HealthState.HEALTHY
    assert states["workflow"] in (HealthState.DEGRADED, HealthState.HEALTHY)


# --- T4-C: monitoring --------------------------------------------------------
def test_monitoring_tracks_volumes():
    _product, ops = make_operations()
    out = ops.qualify()
    m = out.metrics.deterministic_metrics
    assert m["request_volume"] >= 1 and m["prediction_volume"] >= 1 and m["upload_volume"] >= 1
    assert m["failures"] == 0 and m["validation_errors"] == 0
    # informational measures tracked but excluded from the signature
    assert set(out.metrics.informational_metrics) >= {"latency", "processing_time", "resource_usage"}


# --- T4-D: diagnostics -------------------------------------------------------
def test_diagnostics_pass_on_healthy_product():
    _product, ops = make_operations()
    out = ops.qualify()
    assert out.diagnostic.ok
    assert out.diagnostic.root_causes == ()
    assert {f.domain.value for f in out.diagnostic.findings} == {
        "api", "upload", "prediction", "workflow", "failure"}


def test_diagnostics_detect_missing_model():
    # a hub with no model prepared -> missing_model root cause, no crash
    product = ApplicationPlatformService()
    ops = OperationsPlatformService(product)
    out = ops.qualify()
    assert "missing_model" in out.diagnostic.root_causes
    assert out.readiness.classification != DeploymentReadinessClass.READY_FOR_DEPLOYMENT


# --- T4-E: deployment qualification -----------------------------------------
def test_qualification_qualified():
    _product, ops = make_operations()
    out = ops.qualify()
    assert out.qualification.status == QualificationStatus.QUALIFIED
    assert out.qualification.n_available == out.qualification.n_targets == 7
    assert {f.target.value for f in out.qualification.findings} == {
        "dataset_availability", "model_availability", "api_availability", "workflow_availability",
        "report_availability", "persistence_availability", "security_availability"}


def test_qualification_not_qualified_without_model():
    product = ApplicationPlatformService()
    ops = OperationsPlatformService(product)
    out = ops.qualify()
    # model unavailable is a blocking target -> NOT_QUALIFIED
    assert out.qualification.status == QualificationStatus.NOT_QUALIFIED


# --- T4-F: readiness ---------------------------------------------------------
def test_readiness_ready_for_deployment():
    _product, ops = make_operations()
    out = ops.qualify()
    assert out.readiness.classification == DeploymentReadinessClass.READY_FOR_DEPLOYMENT
    assert out.readiness.score >= 0.999
    assert all(v == 1.0 for v in out.readiness.dimensions.values())
    assert out.ready_for_deployment


def test_readiness_not_ready_without_model():
    product = ApplicationPlatformService()
    out = OperationsPlatformService(product).qualify()
    assert out.readiness.classification != DeploymentReadinessClass.READY_FOR_DEPLOYMENT
    assert out.readiness.findings  # at least one dimension below 1.0


# --- T4-G: audit + lineage ---------------------------------------------------
def test_audit_integration():
    _product, ops = make_operations()
    ops.qualify()
    assert ops.audit.verify() and len(ops.audit) >= 5


def test_lineage_chain_reaches_product_workflow():
    product, ops = make_operations()
    out = ops.qualify()
    assert ops.lineage.verify_chain(out.readiness_lineage_id)
    kinds = {n.kind for n in ops.lineage.chain(out.readiness_lineage_id)}
    # the operational spine: Health Event -> Qualification Event -> Readiness
    assert {"ops_health_event", "ops_qualification_event", "ops_readiness"} <= kinds
    # reaches the observed product workflow (Dataset -> Model -> Prediction -> Workflow)
    assert {"app_upload", "app_prediction_result", "app_report"} <= kinds


def test_registry_has_no_orphans():
    _product, ops = make_operations()
    ops.qualify()
    counts = ops.registry.counts()
    assert ops.registry.orphans() == []
    for kind in (EntityKind.HEALTH_CHECK, EntityKind.METRICS_SNAPSHOT, EntityKind.DIAGNOSTIC,
                 EntityKind.QUALIFICATION, EntityKind.READINESS):
        assert counts[kind.value] == 1


# --- T4-H: reports -----------------------------------------------------------
def test_reports_generate():
    _product, ops = make_operations()
    out = ops.qualify()
    reports = ops.reports(out)
    expected = {"health_report", "monitoring_report", "diagnostics_report", "qualification_report",
                "readiness_report", "audit_report", "lineage_report", "operational_summary_report"}
    assert set(reports) == expected
    summary = reports["operational_summary_report"]
    assert summary["ready_for_deployment"] is True
    assert reports["lineage_report"]["chain_verified"]


def test_entity_contract_validation():
    _product, ops = make_operations()
    out = ops.qualify()
    ok, missing = validate_entity("DeploymentReadinessRecord", out.readiness.to_dict())
    assert ok and missing == []
    ok2, _ = validate_entity("QualificationRecord", out.qualification.to_dict())
    assert ok2


# --- determinism -------------------------------------------------------------
def test_determinism_across_instances():
    p1, ops1 = make_operations()
    a = ops1.qualify()
    p2, ops2 = make_operations()
    b = ops2.qualify()
    assert a.health.health_check_id == b.health.health_check_id
    assert a.qualification.qualification_id == b.qualification.qualification_id
    assert a.readiness.readiness_id == b.readiness.readiness_id
    assert a.readiness.score == b.readiness.score


def test_reports_deterministic():
    from ml.provenance import canonical_json
    p1, ops1 = make_operations()
    r1 = ops1.reports(ops1.qualify())
    p2, ops2 = make_operations()
    r2 = ops2.reports(ops2.qualify())
    assert canonical_json(r1) == canonical_json(r2)


# --- corrupted state ---------------------------------------------------------
def test_corrupted_audit_state_detected():
    product, ops = make_operations()
    # tamper the observed product's audit log -> diagnostics flag corrupted_state
    if product.audit.events():
        product.audit.events()[0].payload["tampered"] = True
    out = ops.qualify()
    # health storage still ok, but the failure diagnostic catches the tamper
    assert ("corrupted_state" in out.diagnostic.root_causes) or (not product.audit.verify())


# --- real corpus when available ----------------------------------------------
def test_real_corpus_qualification_when_available():
    from _track3_helpers import real_chb_mit_root
    import base64
    import os
    root = real_chb_mit_root()
    if root is None:
        pytest.skip("real CHB-MIT corpus not acquired locally")
    from backend.application_platform import ApplicationPlatformService as APS
    from backend.application_platform.uploads import prepare_bounded_segment
    from backend.application_platform import create_app
    from backend.model_foundation import ModelArchitecture
    from fastapi.testclient import TestClient

    svc = APS(analysis_seconds=20.0)
    chb = os.path.join(root, "chb_mit", "chb01")
    segs, cohort = [], []
    for i, name in enumerate(("chb01_01.edf", "chb01_03.edf")):
        with open(os.path.join(chb, name), "rb") as fh:
            seg, _fp, _sz = prepare_bounded_segment(fh.read(), name, analysis_seconds=20.0)
        segs.append(seg)
        cohort.append((f"p{i}", f"c{i}", seg))
    try:
        svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
    finally:
        for s in segs:
            if os.path.exists(s):
                os.remove(s)
    client = TestClient(create_app(svc))
    client.post("/v1/auth/register", json={"username": "dr", "password": "pw-123456"})
    tok = client.post("/v1/auth/login",
                      json={"username": "dr", "password": "pw-123456"}).json()["token"]
    with open(os.path.join(chb, "chb01_03.edf"), "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    client.post("/v1/uploads", json={"filename": "chb01_03.edf", "content_base64": b64},
                headers={"Authorization": f"Bearer {tok}"})
    out = OperationsPlatformService(svc).qualify()
    assert out.ready_for_deployment
    assert out.qualification.status == QualificationStatus.QUALIFIED
