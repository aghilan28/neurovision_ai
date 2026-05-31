"""End-to-end test for DRP-2 — Production Model Program.

Demonstrates the full required deliverable: real EEG (P1) -> clean (P2) -> features (P3)
-> the production-model program trains, evaluates, benchmarks, compares, scores readiness,
tracks lineage, and audits the lifecycle for every architecture — whose readiness chain
verifies Patient -> ... -> Feature -> Dataset -> Training Run -> Training Experiment ->
Model -> Benchmark -> Readiness Assessment. Also shows integration with the DRP-1 real
dataset registrations (built on existing feature assets, no replacement systems).
"""

from __future__ import annotations

import dataclasses

from backend.production_models import (
    ProductionModelService, ProductionArchitecture, PRODUCTION_ARCHITECTURES, ReadinessClass,
)
from backend.dataset_integration import DatasetIntegrationService, ReadinessClass as DSReady

from _drp2_helpers import build_feature_cohort


def test_full_deliverable_train_eval_benchmark_compare_readiness(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)

    outs = svc.develop_all(feats, dataset_key="cohort", seed=7)
    assert len(outs) == len(PRODUCTION_ARCHITECTURES)

    # every architecture is trained, evaluated, benchmarked, scored, traceable, audited
    for out in outs.values():
        assert out.accepted
        assert out.readiness.classification == ReadinessClass.READY
        assert svc.integrity(out.model).ok
        assert tracker.verify_chain(out.readiness.lineage_id)

    # compare + recommend
    comparison = svc.compare(outs)
    assert comparison["recommended_model"] in {o.model_id for o in outs.values()}

    # all nine reports generate for a representative model
    rep = next(iter(outs.values()))
    reports = svc.reports(rep.model, comparison=comparison)
    expected = {"training_report", "benchmark_report", "evaluation_report", "comparison_report",
                "readiness_report", "registry_report", "audit_report", "lineage_report",
                "model_summary_report"}
    assert expected == set(reports)
    assert reports["model_summary_report"]["ok"]
    assert reports["lineage_report"]["chain_verified"]

    # the shared registries hold exactly the production models + the single dataset
    assert len(svc.model_registry.list_models()) == len(PRODUCTION_ARCHITECTURES)
    assert len(svc.dataset_registry.list_datasets()) == 1
    assert svc.production_registry.orphans() == []


def test_integrates_with_drp1_dataset_registrations(eeg_fixtures, tmp_path):
    """DRP-2 builds on DRP-1: the same shared lineage tracker carries both the registered
    external corpora (DRP-1) and the production models trained from feature assets."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)

    # DRP-1: register the mandatory real corpora on the shared tracker
    di = DatasetIntegrationService(lineage_tracker=tracker)
    ds_outcomes = di.register_all_mandatory()
    assert all(o.readiness.classification == DSReady.READY for o in ds_outcomes.values())

    # DRP-2: develop production models from the existing feature assets
    svc = ProductionModelService(lineage_tracker=tracker)
    out = svc.develop_model(feats, architecture=ProductionArchitecture.HYBRID_EEG,
                            dataset_key="cohort", seed=7)
    assert out.accepted and svc.integrity(out.model).ok
    # both subsystems coexist on the one shared lineage tracker (no parallel systems)
    assert tracker.verify_chain(out.readiness.lineage_id)
    assert di.lineage is tracker and svc.lineage is tracker


def test_corrupted_benchmark_metadata_fails_content_validation(eeg_fixtures, tmp_path):
    """A benchmark with corrupted (missing) deterministic metrics must fail validation —
    nothing fails silently."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    out = svc.develop_model(feats, architecture=ProductionArchitecture.EEGNET, seed=7)

    corrupted = dataclasses.replace(out.benchmark, deterministic_metrics={"accuracy": 0.5})
    name, passed, _ = svc.content_validator.benchmark_integrity(corrupted)
    assert name == "benchmark_integrity" and passed is False


def test_quarantined_when_not_reproducible(eeg_fixtures, tmp_path, monkeypatch):
    """If a training run is not reproducible, the model is QUARANTINED (not READY)."""
    import backend.production_models.service as service_mod

    real_train = service_mod.train_production

    def fake_train(config, bundle, *, created_at="1970-01-01T00:00:00Z"):
        res = real_train(config, bundle, created_at=created_at)
        return dataclasses.replace(res, reproducible=False,
                                   record=dataclasses.replace(res.record, reproducible=False))

    monkeypatch.setattr(service_mod, "train_production", fake_train)
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    out = svc.develop_model(feats, architecture=ProductionArchitecture.EEGNET, seed=7)
    from backend.production_models import ModelStatus
    assert out.model.status == ModelStatus.QUARANTINED
    assert out.readiness.classification != ReadinessClass.READY
