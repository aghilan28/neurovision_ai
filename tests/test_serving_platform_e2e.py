"""End-to-end test for DRP-3 — Production Serving Platform.

Demonstrates the full required deliverable: real EEG (P1) -> clean (P2) -> features (P3)
-> trained model -> the serving platform receives a request, selects a model, executes
inference (reusing the inference foundation), generates + delivers a response, tracks the
lifecycle, scores readiness, traces lineage, and audits the execution — whose response
chain verifies Dataset -> Feature -> Model -> Inference -> Serving Request -> Serving
Execution -> Serving Response. Also shows coexistence with the DRP-1 dataset registrations
and the DRP-2 production-model program on one shared lineage tracker.
"""

from __future__ import annotations

import dataclasses

from backend.model_foundation import ModelArchitecture
from backend.serving_platform import (
    ServingPlatformService, PredictionRequestContract, ServingStatus, ReadinessClass,
    ServingContentValidator,
)
from backend.dataset_integration import DatasetIntegrationService, ReadinessClass as DSReady
from backend.production_models import ProductionModelService, ProductionArchitecture

from _drp3_helpers import build_feature_cohort, train_model


def test_full_serving_deliverable_for_every_architecture(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ServingPlatformService(lineage_tracker=tracker)

    # load one model per architecture (no training happens in the serving platform itself)
    models = {}
    for arch in ModelArchitecture:
        model = train_model(tracker, feats, architecture=arch)
        svc.load_model(model, feats, dataset_key="cohort")
        models[arch.value] = model

    for arch_value, model in models.items():
        req = PredictionRequestContract(
            model_ref={"model_id": model.model_id}, feature_asset_id=feats[0].feature_asset_id,
            case_id=feats[0].case_id, patient_id=feats[0].patient_id)
        out = svc.serve(req, feats[0])
        assert out.accepted and out.reason == ServingStatus.COMPLETED.value
        assert out.readiness.classification == ReadinessClass.READY
        assert svc.integrity(out.execution).ok
        assert tracker.verify_chain(out.execution.response.lineage_id)
        # all nine reports
        assert len(svc.reports(out.execution)) == 9

    # every served execution is registered, orphan-free, and traceable
    assert len(svc.registry.list_executions()) == len(models)
    assert svc.registry.orphans() == []


def test_serving_coexists_with_drp1_datasets_and_drp2_models(eeg_fixtures, tmp_path):
    """DRP-3 builds on DRP-1 + DRP-2: external corpora (DRP-1), production models (DRP-2),
    and served predictions (DRP-3) all share one lineage tracker (no parallel systems)."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)

    # DRP-1: register real corpora on the shared tracker
    di = DatasetIntegrationService(lineage_tracker=tracker)
    ds_outcomes = di.register_all_mandatory()
    assert all(o.readiness.classification == DSReady.READY for o in ds_outcomes.values())

    # DRP-2: develop a production-candidate model on the shared tracker
    pm = ProductionModelService(lineage_tracker=tracker)
    prod = pm.develop_model(feats, architecture=ProductionArchitecture.EEGNET,
                            dataset_key="cohort", seed=7)
    assert prod.accepted

    # DRP-3: serve a model-foundation model (the inference-foundation-servable artifact)
    model = train_model(tracker, feats, architecture=ModelArchitecture.EEGNET)
    svc = ServingPlatformService(lineage_tracker=tracker)
    svc.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(model_ref={"model_id": model.model_id},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = svc.serve(req, feats[0])
    assert out.accepted and svc.integrity(out.execution).ok
    # all four subsystems share the one tracker
    assert di.lineage is tracker and pm.lineage is tracker and svc.lineage is tracker


def test_corrupted_response_fails_validation(eeg_fixtures, tmp_path):
    """A response whose probability vector is the wrong width must fail response integrity —
    nothing passes silently."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    model = train_model(tracker, feats)
    svc = ServingPlatformService(lineage_tracker=tracker)
    svc.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(model_ref={"model_id": model.model_id},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = svc.serve(req, feats[0])
    corrupted = dataclasses.replace(out.execution.response, probability_scores=(0.5,))
    name, passed, _ = ServingContentValidator().response_integrity(
        corrupted, model.metadata.n_classes)
    assert name == "response_integrity" and passed is False


def test_reload_and_reserve_is_deterministic(eeg_fixtures, tmp_path):
    """Serving the same request twice yields the same execution id + version (idempotent)."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    model = train_model(tracker, feats)
    svc = ServingPlatformService(lineage_tracker=tracker)
    svc.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(model_ref={"model_id": model.model_id},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    a = svc.serve(req, feats[0]).execution
    b = svc.serve(req, feats[0]).execution
    assert a.execution_id == b.execution_id and a.version.version == b.version.version
