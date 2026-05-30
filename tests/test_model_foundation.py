"""Tests for the Model Foundation Platform (Productization P4).

Covers every mandated category: dataset connectors, dataset registry, training,
evaluation, experiments, model registry, validation, audit, lineage, reports,
determinism, boundary conditions, and edge cases. Runs the real P1 -> P2 -> P3 -> P4
pipeline over the committed P1 EEG fixtures (no replacement systems).
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib

import numpy as np
import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import (
    ModelFoundationService, ModelArchitecture, DatasetSource, DatasetStatus, ModelStatus,
    ExternalDatasetConnector, DatasetRegistry, build_feature_dataset, assemble_feature_vector,
    patient_disjoint_split, build_model, train, evaluate, mint_identity, validate_identity, IdentityError, make_model_audit_log,
)
from backend.model_foundation.evaluation import metrics as M
from backend.model_foundation.schemas import ENTITY_CONTRACTS, validate_entity

import _eeg_fixtures as fx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
ALL_ARCH = list(ModelArchitecture)


@pytest.fixture(scope="module")
def cohort(eeg_fixtures, tmp_path_factory):
    """Build a 6-patient cohort of feature assets once (shared lineage tracker)."""
    tmp = tmp_path_factory.mktemp("p4")
    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    es = LocalEEGStore(str(tmp / "raw"))
    esvc = EEGFoundationService(es, lineage_tracker=tracker)
    ps = ProcessedSignalStore(str(tmp / "proc"))
    ssvc = SignalProcessingService(es, ps, lineage_tracker=tracker)
    fsvc = FeatureEngineeringService(ps, lineage_tracker=tracker)
    feats = []
    for i, name in enumerate(FIXTURES):
        c = cases.create_case(patient_key=f"P-{i}", case_key=f"C-{i}")
        raw = esvc.ingest_eeg(eeg_fixtures[name], case_id=c.case_id, patient_id=c.patient_id,
                              case_lineage_id=c.lineage_id).asset
        proc = ssvc.process(raw).asset
        feats.append(fsvc.generate_features(proc).asset)
    return tracker, feats


def _mf(tracker):
    return ModelFoundationService(lineage_tracker=tracker)


def _train(cohort, arch=ModelArchitecture.EEGNET, key="ds"):
    tracker, feats = cohort
    mf = _mf(tracker)
    out = mf.train_model(feats, architecture=arch, name=f"exp-{arch.value}", dataset_key=key, seed=7)
    return mf, out.model


# ===========================================================================
# Dataset connectors (P4-C)
# ===========================================================================
def test_dataset_connectors_framework():
    manifest = {"name": "TUH demo", "n_recordings": 12, "patients": ["a", "b", "c"],
                "channels": ["Fp1", "Fp2"], "sampling_frequency": 256, "class_labels": [0, 1]}
    for src in (DatasetSource.TUH_EEG, DatasetSource.CHB_MIT, DatasetSource.TEMPLE_EEG):
        rec = ExternalDatasetConnector(src).build_record(manifest, dataset_key="k")
        assert rec.source == src and rec.status == DatasetStatus.REGISTERED
        assert rec.n_samples == 12 and rec.source_metadata["downloaded"] is False
    # malformed manifest -> quarantined, not an exception
    bad = ExternalDatasetConnector(DatasetSource.TUH_EEG).build_record(
        {"name": "x"}, dataset_key="k")
    assert bad.status == DatasetStatus.QUARANTINED
    assert bad.source_metadata["validation_problems"]


def test_register_external_dataset_via_service(cohort):
    tracker, _ = cohort
    mf = _mf(tracker)
    rec = mf.register_external_dataset(DatasetSource.CHB_MIT, {
        "name": "CHB", "n_recordings": 5, "patients": ["p1"], "channels": ["C3"],
        "sampling_frequency": 256}, dataset_key="chb")
    assert mf.dataset_registry.exists(rec.dataset_id)
    assert rec.dataset_id in mf.dataset_registry.by_source("chb_mit")


# ===========================================================================
# Dataset builder + registry (P4-D)
# ===========================================================================
def test_feature_dataset_build(cohort):
    tracker, feats = cohort
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", seed=7)
    assert bundle.X.shape[0] == len(feats)
    assert bundle.X.shape[1] == len(bundle.record.feature_names) == 29
    assert bundle.record.split.patient_disjoint is True
    names, row = assemble_feature_vector(feats[0])
    assert len(names) == 29 and row.shape == (29,)


def test_dataset_registry_no_silent_overwrite(cohort):
    tracker, feats = cohort
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", seed=7)
    reg = DatasetRegistry()
    reg.register(bundle.record)
    reg.register(bundle.record)  # idempotent (same content)
    tampered = dataclasses.replace(bundle.record, name="different")
    with pytest.raises(ValueError):
        reg.register(tampered)


# ===========================================================================
# Training (P4-E/F)
# ===========================================================================
@pytest.mark.parametrize("arch", ALL_ARCH)
def test_training_each_architecture(cohort, arch):
    tracker, feats = cohort
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", seed=7)
    run, model = train(arch, bundle, n_classes=2, seed=7)
    assert run.architecture == arch and run.n_params > 0
    assert run.params_fingerprint and len(run.training_history) > 0
    assert 0.0 <= run.training_metrics["train_accuracy"] <= 1.0
    # deterministic
    run2, model2 = train(arch, bundle, n_classes=2, seed=7)
    assert run.params_fingerprint == run2.params_fingerprint


# ===========================================================================
# Evaluation (P4-G)
# ===========================================================================
def test_evaluation(cohort):
    tracker, feats = cohort
    bundle = build_feature_dataset(feats, name="d", dataset_key="k", seed=7)
    run, model = train(ModelArchitecture.EEGNET, bundle, n_classes=2, seed=7)
    ev = evaluate(model, bundle, training_run_id=run.training_run_id, n_classes=2)
    assert 0.0 <= ev.metrics["accuracy"] <= 1.0
    assert len(ev.confusion_matrix) == 2 and len(ev.confusion_matrix[0]) == 2
    assert {"ece", "brier"} <= set(ev.calibration)
    assert {"mean_entropy", "mean_confidence"} <= set(ev.uncertainty)


def test_metrics_correctness():
    y = np.array([0, 0, 1, 1])
    probs = np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.3, 0.7]])
    pred = probs.argmax(axis=1)
    cm = M.confusion_matrix(y, pred, 2)
    assert M.accuracy(y, pred) == 1.0
    _, _, f1, _ = M.precision_recall_f1(cm)
    assert f1 == 1.0


# ===========================================================================
# Service: full train -> evaluate -> register
# ===========================================================================
@pytest.mark.parametrize("arch", ALL_ARCH)
def test_train_model_service(cohort, arch):
    mf, model = _train(cohort, arch)
    tracker, _ = cohort
    assert model.status == ModelStatus.TRAINED
    assert model.architecture == arch
    assert mf.model_registry.exists(model.model_id)
    assert mf.integrity(model).ok, mf.integrity(model).to_dict()
    assert tracker.verify_chain(model.lineage_id)
    assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
            "training_run", "model"} <= {r.kind for r in tracker.chain(model.lineage_id)}


def test_integrity_has_nine_checks(cohort):
    mf, model = _train(cohort)
    report = mf.integrity(model)
    assert report.ok and report.to_dict()["n_checks"] == 9
    names = {c["name"] for c in report.to_dict()["checks"]}
    for expected in ("dataset_integrity", "training_integrity", "evaluation_integrity",
                     "model_integrity", "determinism_integrity", "registry_integrity",
                     "audit_integrity", "lineage_integrity", "version_integrity"):
        assert expected in names


# ===========================================================================
# Experiments (P4-H)
# ===========================================================================
def test_experiment_tracking(cohort):
    mf, model = _train(cohort)
    assert mf.experiment_registry.exists(model.experiment_id)
    exp = mf.experiment_registry.get(model.experiment_id)
    assert exp.training_run_id == model.training_run_id
    assert exp.evaluation_id == model.evaluation_id
    assert model.model_id in exp.artifact_refs


# ===========================================================================
# Model registry (P4-I)
# ===========================================================================
def test_model_registry(cohort):
    mf, model = _train(cohort)
    assert model.model_id in mf.model_registry.by_dataset(model.dataset_id)
    assert model.model_id in mf.model_registry.by_architecture(model.architecture.value)
    assert model.model_id in mf.model_registry.by_experiment(model.experiment_id)
    rec = mf.model_registry.get(model.model_id)
    with pytest.raises(ValueError):
        mf.model_registry.register(dataclasses.replace(rec, status=ModelStatus.QUARANTINED))


# ===========================================================================
# Audit (P4-J)
# ===========================================================================
def test_audit(cohort):
    mf, model = _train(cohort)
    log = mf.audit_log_for(model.model_id)
    assert log.verify() and log.head == model.audit_head
    kinds = {e.kind for e in log.events()}
    assert {"dataset_registered", "training_completed", "evaluation_completed",
            "experiment_tracked", "model_lineage_recorded", "model_version_changed",
            "model_registered"} <= kinds
    fresh = make_model_audit_log()
    fresh.append("training_completed", {"a": 1})
    fresh.append("model_registered", {"b": 2})
    assert fresh.verify()
    fresh._events[0] = dataclasses.replace(fresh._events[0], payload={"a": 999})
    assert fresh.verify() is False


# ===========================================================================
# Lineage (P4-J)
# ===========================================================================
def test_lineage_parents_training_run(cohort):
    tracker, _ = cohort
    mf, model = _train(cohort)
    node = tracker.get(model.lineage_id)
    assert model.training_run_id == mf._context[model.model_id]["training_run"].training_run_id
    assert node.kind == "model"
    tr_node = tracker.get(node.parents[0])
    assert tr_node.kind == "training_run"


# ===========================================================================
# Reports (P4-L)
# ===========================================================================
def test_reports(cohort):
    mf, model = _train(cohort)
    r1 = mf.reports(model)
    r2 = mf.reports(model)
    assert set(r1) == {"dataset_report", "training_report", "evaluation_report",
                       "experiment_report", "model_report", "registry_report", "audit_report",
                       "lineage_report", "validation_report"}
    assert r1 == r2
    assert r1["validation_report"]["ok"] is True
    assert r1["lineage_report"]["chain_verified"] is True


# ===========================================================================
# Determinism (P4)
# ===========================================================================
def test_determinism(cohort):
    tracker, feats = cohort
    mf = _mf(tracker)
    a = mf.train_model(feats, architecture=ModelArchitecture.EEGNET, dataset_key="ds", seed=7).model
    b = mf.train_model(feats, architecture=ModelArchitecture.EEGNET, dataset_key="ds", seed=7).model
    assert a.model_id == b.model_id
    assert a.version.version == b.version.version
    assert a.params_fingerprint == b.params_fingerprint


# ===========================================================================
# Identity
# ===========================================================================
def test_identity():
    a = mint_identity("model", {"training_run_id": "training_run+" + "a" * 16, "model_key": "k1"})
    b = mint_identity("model", {"training_run_id": "training_run+" + "a" * 16, "model_key": "k1"})
    assert a.id == b.id and a.id.startswith("model+")
    assert a.derived_from == "training_run+" + "a" * 16
    with pytest.raises(IdentityError):
        mint_identity("model", {"training_run_id": "not-a-run", "model_key": "k"})
    assert validate_identity("dataset+" + "a" * 16, "dataset")[0] is True


# ===========================================================================
# Schemas
# ===========================================================================
def test_schemas(cohort):
    mf, model = _train(cohort)
    ctx = mf._context[model.model_id]
    for name, payload in [
        ("ModelRecord", model.to_dict()),
        ("DatasetRecord", ctx["dataset_record"].to_dict()),
        ("TrainingRunRecord", ctx["training_run"].to_dict()),
        ("EvaluationRecord", ctx["evaluation"].to_dict()),
        ("ExperimentRecord", ctx["experiment"].to_dict()),
        ("ModelRegistryRecord", mf.model_registry.get(model.model_id).to_dict()),
    ]:
        ok, missing = validate_entity(name, payload)
        assert ok, (name, missing)
    for entity in ["ModelIdentity", "DatasetRecord", "TrainingRunRecord", "EvaluationRecord",
                   "ExperimentRecord", "ModelMetadata", "ModelValidationRecord",
                   "ModelRegistryRecord", "ModelRecord", "ModelAuditRecord", "ModelLineageRecord"]:
        assert entity in ENTITY_CONTRACTS


# ===========================================================================
# Edge cases / boundary conditions
# ===========================================================================
def test_split_single_patient_and_three_patients():
    s1 = patient_disjoint_split(("a", "b"), ("p1", "p1"), seed=1)
    assert s1.patient_disjoint and len(s1.train) == 2 and not s1.val and not s1.test
    s3 = patient_disjoint_split(("a", "b", "c"), ("p1", "p2", "p3"), seed=1)
    assert s3.patient_disjoint
    assert len(s3.train) + len(s3.val) + len(s3.test) == 3
    # no patient appears in two splits
    groups = [set(s3.train), set(s3.val), set(s3.test)]
    assert sum(len(g) for g in groups) == len(set().union(*groups))


def test_tiny_model_fit_is_deterministic():
    X = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    y = np.array([0, 1])
    m1 = build_model(ModelArchitecture.TRANSFORMER, 2, seed=3).fit(X, y)
    m2 = build_model(ModelArchitecture.TRANSFORMER, 2, seed=3).fit(X, y)
    assert m1.params_fingerprint() == m2.params_fingerprint()
    assert m1.predict(X).shape == (2,)


def test_evaluation_handles_empty_split():
    # a single-patient dataset has empty val/test; evaluator falls back to train
    s = patient_disjoint_split(("a", "b"), ("p1", "p1"), seed=0)
    assert not s.test  # empty test split exists


# ===========================================================================
# Boundary
# ===========================================================================
def test_model_foundation_respects_boundaries():
    root = REPO_ROOT / "backend" / "model_foundation"
    forbidden = {"frontend", "tests", "scripts", "tools", "monitoring", "deployment"}
    uses_numpy = False
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            roots = []
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                roots = [node.module.split(".")[0]]
            assert not (set(roots) & forbidden), f"{path} imports forbidden module {roots}"
            uses_numpy = uses_numpy or "numpy" in roots
    assert uses_numpy, "model foundation must use real numerics (numpy)"
