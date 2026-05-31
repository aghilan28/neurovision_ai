"""Tests for DRP-2 — Production Model Program (``backend/production_models``).

Exercises the architecture framework, training, benchmarking, evaluation, readiness,
registry/audit/lineage integration, reports, schemas, and boundary/invalid/corrupted/
missing conditions — using the **real** P1->P3 feature assets (no replacement systems).
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from backend.production_models import (
    ProductionModelService, ProductionArchitecture, ModelStatus, ReadinessClass,
    PRODUCTION_ARCHITECTURES, build_production_model, architecture_catalog, ReadinessEngine,
    TrainingConfig, train_production, benchmark_model,
    ProductionModelRegistry, RegistryError, ENTITY_CONTRACTS, validate_entity, ProductionModelError,
    HybridModel, mint_identity,
)
from backend.production_models.benchmarking import metrics as RM
from backend.model_foundation import build_feature_dataset

from _drp2_helpers import build_feature_cohort


# =============================================================================
# Architecture framework (DRP2-C)
# =============================================================================
def test_five_architectures_build_and_share_a_uniform_contract():
    assert [a.value for a in PRODUCTION_ARCHITECTURES] == [
        "eegnet", "deepconvnet", "temporal_cnn", "transformer_eeg", "hybrid_eeg"]
    rng = np.random.default_rng(0)
    X = rng.standard_normal((24, 10))
    y = (X[:, 0] > 0).astype(int)
    for arch in PRODUCTION_ARCHITECTURES:
        m = build_production_model(arch, 2, seed=7)
        m.fit(X, y)
        assert m.predict_proba(X).shape == (24, 2)
        assert m.n_params() > 0 and m.params_fingerprint()
        spec = m.architecture_spec()
        assert spec["production_architecture"] == arch.value


def test_reference_wrappers_reuse_reference_models_without_removing_them():
    # the four standard archs map onto the (still-present) model-foundation reference models
    from backend.model_foundation import ModelArchitecture as Ref
    cat = {c["architecture"]: c for c in architecture_catalog()}
    assert cat["eegnet"]["reference_architecture"] == Ref.EEGNET.value
    assert cat["hybrid_eeg"]["reference_architecture"] is None
    assert cat["hybrid_eeg"]["family"] == "hybrid"


def test_hybrid_is_deterministic_across_instances():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((30, 8))
    y = (X[:, 1] > 0).astype(int)
    a = HybridModel(2, seed=11).fit(X, y)
    b = HybridModel(2, seed=11).fit(X, y)
    assert a.params_fingerprint() == b.params_fingerprint()


# =============================================================================
# Benchmarking ranking metrics (DRP2-E)
# =============================================================================
def test_roc_auc_and_pr_auc_are_correct_on_known_inputs():
    y = np.array([0, 0, 1, 1])
    probs_perfect = np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]])
    assert RM.roc_auc_macro(y, probs_perfect) == pytest.approx(1.0)
    assert RM.pr_auc_macro(y, probs_perfect) == pytest.approx(1.0)
    # a single-class y yields a degenerate (0.0) macro ROC-AUC, never a crash
    assert RM.roc_auc_macro(np.array([1, 1, 1]), np.ones((3, 2)) * 0.5) == 0.0


# =============================================================================
# Training (DRP2-D)
# =============================================================================
def test_training_is_reproducible(eeg_fixtures, tmp_path):
    _, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", n_classes=2, seed=7)
    cfg = TrainingConfig(architecture=ProductionArchitecture.TEMPORAL_CNN, seed=7, n_classes=2)
    r1 = train_production(cfg, bundle)
    r2 = train_production(cfg, bundle)
    assert r1.reproducible and r2.reproducible
    assert r1.params_fingerprint == r2.params_fingerprint
    assert r1.record.training_run_id == r2.record.training_run_id
    assert r1.record.n_params > 0 and r1.record.training_history


def test_training_rejects_empty_split():
    class _Empty:
        record = type("R", (), {"dataset_id": "dataset+" + "0" * 16})()

        def split_indices(self, name):
            return np.array([], dtype=int)
    from backend.production_models import TrainingError
    cfg = TrainingConfig(architecture=ProductionArchitecture.EEGNET, seed=1, n_classes=2)
    with pytest.raises(TrainingError):
        train_production(cfg, _Empty())


# =============================================================================
# Benchmark determinism: timings informational, metrics hashed (DRP2-E)
# =============================================================================
def test_benchmark_id_excludes_timings(eeg_fixtures, tmp_path):
    _, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", n_classes=2, seed=7)
    cfg = TrainingConfig(architecture=ProductionArchitecture.EEGNET, seed=7, n_classes=2)
    tr = train_production(cfg, bundle)
    model_id = mint_identity("production_model",
                             {"training_run_id": tr.training_run_id,
                              "model_key": tr.params_fingerprint}).id
    b1 = benchmark_model(tr.model, bundle, model_id=model_id,
                         architecture=ProductionArchitecture.EEGNET, n_classes=2,
                         training_time_ms=1.0)
    b2 = benchmark_model(tr.model, bundle, model_id=model_id,
                         architecture=ProductionArchitecture.EEGNET, n_classes=2,
                         training_time_ms=999.0)
    # different measured timings, identical deterministic id + signature
    assert b1.benchmark_id == b2.benchmark_id
    assert b1.metrics_signature() == b2.metrics_signature()
    required = {"accuracy", "precision_macro", "recall_macro", "f1_macro",
                "roc_auc_macro", "pr_auc_macro", "ece", "brier"}
    assert required <= set(b1.deterministic_metrics)
    assert {"latency_ms_per_sample", "peak_memory_kb", "training_time_ms",
            "inference_time_ms"} <= set(b1.performance)


# =============================================================================
# End-to-end service: develop + integrity + registry/audit/lineage (DRP2-H/I)
# =============================================================================
def test_develop_all_architectures(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    outs = svc.develop_all(feats, dataset_key="cohort", seed=7)
    assert set(outs) == {a.value for a in PRODUCTION_ARCHITECTURES}

    for arch, out in outs.items():
        m = out.model
        assert out.accepted and m.status == ModelStatus.CANDIDATE
        # registry integration: production registry + shared dataset/model registries
        assert svc.production_registry.exists(m.model_id)
        assert svc.model_registry.exists(m.model_id)          # shared base-model registry
        assert svc.dataset_registry.exists(m.dataset_id)      # shared dataset registry
        # benchmark + evaluation + readiness all present
        assert out.benchmark is not None and out.evaluation is not None
        assert out.readiness.classification == ReadinessClass.READY
        # integrity (all mandated checks pass)
        report = svc.integrity(m)
        assert report.ok, [c.name for c in report.failures()]
        # audit integrity
        log = svc.audit_log_for(m.model_id)
        assert log.verify() and m.audit_head == log.head
        # lineage reaches the patient
        assert tracker.verify_chain(out.readiness.lineage_id)
        kinds = {r.kind for r in tracker.chain(out.readiness.lineage_id)}
        assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                "training_run", "training_experiment", "model", "benchmark",
                "readiness_assessment"} <= kinds
        # the production model is immutable
        with pytest.raises(dataclasses.FrozenInstanceError):
            m.status = ModelStatus.QUARANTINED

    # no parallel registries: ONE shared dataset for the whole cohort; no orphans
    assert len(svc.dataset_registry.list_datasets()) == 1
    assert svc.production_registry.orphans() == []
    counts = svc.production_registry.counts()
    assert counts["production_model"] == 5 and counts["benchmark"] == 5


def test_model_comparison_recommends_a_model(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    outs = svc.develop_all(feats, dataset_key="cohort", seed=7)
    comparison = svc.compare(outs)
    assert comparison["n_models"] == 5
    assert comparison["recommended_model"] in {o.model_id for o in outs.values()}
    assert set(comparison["best_per_metric"]) >= {"accuracy", "f1_macro", "roc_auc_macro"}
    assert len(comparison["ranking"]) == 5


def test_compare_requires_two_models(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    out = svc.develop_model(feats, architecture=ProductionArchitecture.EEGNET, seed=7)
    with pytest.raises(ProductionModelError):
        svc.compare([out])


# =============================================================================
# Evaluation analyses (DRP2-F)
# =============================================================================
def test_evaluation_contains_all_analyses(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService(lineage_tracker=tracker)
    out = svc.develop_model(feats, architecture=ProductionArchitecture.HYBRID_EEG, seed=7)
    ev = out.evaluation
    assert ev.confusion_matrix and len(ev.confusion_matrix) == 2
    assert "ece" in ev.calibration_analysis and "brier" in ev.calibration_analysis
    assert "overall_error_rate" in ev.error_analysis
    assert "true_distribution" in ev.class_distribution_analysis
    assert "stability_score" in ev.stability_analysis
    assert ev.reliability_analysis["bins"]


# =============================================================================
# Readiness engine (DRP2-G)
# =============================================================================
def test_readiness_requires_all_evidence():
    eng = ReadinessEngine()
    mid = "production_model+" + "a" * 16
    ready = eng.assess(model_id=mid, training_present=True, evaluation_present=True,
                       benchmark_present=True, registered=True, validation_ok=True,
                       traceable=True, audited=True)
    assert ready.classification == ReadinessClass.READY and ready.score == pytest.approx(1.0)

    # a missing benchmark can never be READY
    missing_bench = eng.assess(model_id=mid, training_present=True, evaluation_present=True,
                               benchmark_present=False, registered=True, validation_ok=True,
                               traceable=True, audited=True)
    assert missing_bench.classification != ReadinessClass.READY
    assert "benchmark_readiness" in missing_bench.findings

    # failed validation forces NOT_READY
    bad = eng.assess(model_id=mid, training_present=True, evaluation_present=True,
                     benchmark_present=True, registered=True, validation_ok=False,
                     traceable=True, audited=True)
    assert bad.classification == ReadinessClass.NOT_READY


# =============================================================================
# Registry orphans + silent-overwrite guard (DRP2-H)
# =============================================================================
def test_registry_rejects_orphan_model():
    from backend.production_models.models.domain import ModelRegistryRecord
    reg = ProductionModelRegistry()
    rec = ModelRegistryRecord(
        model_id="production_model+" + "0" * 16, architecture="eegnet",
        dataset_id="dataset+" + "0" * 16, training_experiment_id="training_experiment+" + "0" * 16,
        benchmark_id="benchmark+" + "0" * 16, model_evaluation_id="model_evaluation+" + "0" * 16,
        readiness_id="readiness+" + "0" * 16, base_evaluation_id="evaluation+" + "0" * 16,
        case_id="case+" + "0" * 16, patient_ids=("patient+" + "0" * 16,),
        status=ModelStatus.CANDIDATE, readiness_class=ReadinessClass.READY, version="v",
        owner="o", creation_date="t", audit_state="", lineage_id="", dependencies=())
    with pytest.raises(RegistryError):       # no lineage node / audit head -> orphan
        reg.register_model(rec)


# =============================================================================
# Schemas (DRP2-K)
# =============================================================================
def test_entity_contracts_cover_all_records():
    for name in ("ProductionModelIdentity", "TrainingExperimentRecord", "ModelBenchmarkRecord",
                 "ModelEvaluationRecord", "ModelReadinessRecord", "ModelValidationRecord",
                 "ModelRegistryRecord", "ProductionModelRecord"):
        assert name in ENTITY_CONTRACTS
    ok, missing = validate_entity("ModelBenchmarkRecord",
                                  {"benchmark_id": "x", "model_id": "y", "architecture": "eegnet",
                                   "dataset_id": "d", "split": "test",
                                   "deterministic_metrics": {}, "performance": {}})
    assert ok and missing == []


# =============================================================================
# Cross-run determinism (NR-9/NR-10)
# =============================================================================
def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path / sub)
        svc = ProductionModelService(lineage_tracker=tracker)
        return svc.develop_model(feats, architecture=ProductionArchitecture.DEEPCONVNET,
                                 dataset_key="cohort", seed=7).model
    a, b = run("a"), run("b")
    assert a.model_id == b.model_id
    assert a.version.version == b.version.version
    assert a.params_fingerprint == b.params_fingerprint


# =============================================================================
# Invalid input / boundary
# =============================================================================
def test_develop_requires_feature_lineage_in_shared_tracker(eeg_fixtures, tmp_path):
    _, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    svc = ProductionModelService()       # fresh tracker WITHOUT the feature nodes
    with pytest.raises(ProductionModelError):
        svc.develop_model(feats, architecture=ProductionArchitecture.EEGNET, seed=7)


def test_develop_requires_feature_assets():
    svc = ProductionModelService()
    with pytest.raises(ProductionModelError):
        svc.develop_model([], architecture=ProductionArchitecture.EEGNET, seed=7)
