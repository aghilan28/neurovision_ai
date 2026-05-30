"""Tests for the Clinical Inference Foundation (Productization P5).

Covers every mandated category: model execution, predictions, confidence, calibration,
explainability, registry, validation, audit, lineage, reports, determinism, boundary
conditions, and edge cases. Runs the real P1 -> P2 -> P3 -> P4 -> P5 pipeline over the
committed P1 EEG fixtures (no replacement systems).
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
from backend.model_foundation import ModelFoundationService, ModelArchitecture
from backend.inference_foundation import (
    InferenceFoundationService, ModelExecutionEngine, ModelExecutionError, ConfidenceEngine, ConfidenceLevel, CalibrationQuality,
    ExplanationMethod, InferenceStatus, mint_identity, validate_identity, IdentityError,
    make_inference_audit_log,
)
from backend.inference_foundation.schemas import ENTITY_CONTRACTS, validate_entity

import _eeg_fixtures as fx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
ALL_ARCH = list(ModelArchitecture)
DATASET_KEY = "cohort"


@pytest.fixture(scope="module")
def ctx(eeg_fixtures, tmp_path_factory):
    """Build a 6-patient cohort + an EEGNet model once (shared lineage tracker)."""
    tmp = tmp_path_factory.mktemp("p5")
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
        feats.append(fsvc.generate_features(ssvc.process(raw).asset).asset)
    mf = ModelFoundationService(lineage_tracker=tracker)
    model = mf.train_model(feats, architecture=ModelArchitecture.EEGNET, dataset_key=DATASET_KEY,
                           seed=7).model
    return tracker, feats, mf, model


def _inf(tracker):
    return InferenceFoundationService(lineage_tracker=tracker)


def _predict(ctx, feature_index=0):
    tracker, feats, mf, model = ctx
    inf = _inf(tracker)
    out = inf.predict(model, feats[feature_index], train_feature_records=feats, dataset_key=DATASET_KEY)
    return inf, out.asset


# ===========================================================================
# Model execution (P5-C)
# ===========================================================================
def test_model_loading_and_verification(ctx):
    tracker, feats, mf, model = ctx
    eng = ModelExecutionEngine()
    fitted, meta, bundle = eng.load_model(model, feats, dataset_key=DATASET_KEY)
    assert meta["params_fingerprint_verified"] and meta["version_verified"]
    assert bundle.X.shape[1] == 29
    # tampered model fails verification (not a silent pass)
    tampered = dataclasses.replace(model, params_fingerprint="0" * 16)
    with pytest.raises(ModelExecutionError):
        eng.load_model(tampered, feats, dataset_key=DATASET_KEY)


def test_input_output_validation(ctx):
    tracker, feats, mf, model = ctx
    eng = ModelExecutionEngine()
    fitted, meta, bundle = eng.load_model(model, feats, dataset_key=DATASET_KEY)
    with pytest.raises(ModelExecutionError):
        eng.validate_input(np.zeros(5), expected_n_features=29)
    with pytest.raises(ModelExecutionError):
        eng.validate_output(np.array([0.3, 0.3]), n_classes=2)  # does not sum to 1


# ===========================================================================
# Predictions (P5-D)
# ===========================================================================
@pytest.mark.parametrize("arch", ALL_ARCH)
def test_predictions_each_architecture(ctx, arch):
    tracker, feats, mf, model = ctx
    m = mf.train_model(feats, architecture=arch, dataset_key=DATASET_KEY, seed=7).model
    inf = _inf(tracker)
    out = inf.predict(m, feats[0], train_feature_records=feats, dataset_key=DATASET_KEY)
    assert out.accepted
    p = out.asset.prediction
    probs = p.probabilities
    assert abs(sum(probs) - 1.0) < 1e-6 and len(probs) == m.metadata.n_classes
    assert p.predicted_class == int(np.argmax(probs))
    assert {s.name for s in p.scores} == {"max_probability", "margin", "normalized_entropy"}


# ===========================================================================
# Confidence (P5-E)
# ===========================================================================
def test_confidence(ctx):
    inf, asset = _predict(ctx)
    c = asset.confidence
    assert 0.0 <= c.confidence_score <= 1.0
    lo, hi = c.confidence_interval
    assert 0.0 <= lo <= hi <= 1.0
    assert 0.0 <= c.prediction_stability <= 1.0 and 0.0 <= c.prediction_reliability <= 1.0
    assert c.confidence_level == ConfidenceLevel.from_score(c.prediction_reliability)
    assert {"normalized_entropy", "margin"} <= set(c.uncertainty_summary)


# ===========================================================================
# Calibration (P5-F)
# ===========================================================================
def test_calibration(ctx):
    inf, asset = _predict(ctx)
    cal = asset.calibration
    assert 0.0 <= cal.expected_calibration_error <= 1.0 and cal.brier_score >= 0.0
    assert cal.calibration_quality == CalibrationQuality.from_ece(cal.expected_calibration_error)
    assert 0.0 <= cal.reliability_assessment <= 1.0 and cal.reference_n_samples > 0


# ===========================================================================
# Explainability (P5-G)
# ===========================================================================
def test_explainability(ctx):
    inf, asset = _predict(ctx)
    e = asset.explanation
    assert e.method == ExplanationMethod.OCCLUSION
    assert len(e.feature_contributions) == 29 and len(e.feature_importance) == 29
    imp_sum = sum(c.contribution for c in e.feature_importance)
    assert abs(imp_sum - 1.0) < 1e-6 or imp_sum == 0.0
    assert set(e.band_importance) == {"delta", "theta", "alpha", "beta", "gamma"}
    assert {"Fp1", "Fp2", "Cz"} == set(e.channel_importance)        # input-derived channel salience
    assert len(e.decision_factors) > 0
    # structured only: every contribution value is numeric (no images/objects)
    assert all(isinstance(c.contribution, float) for c in e.feature_contributions)


# ===========================================================================
# Prediction asset generation + integrity
# ===========================================================================
@pytest.mark.parametrize("arch", ALL_ARCH)
def test_prediction_asset_and_integrity(ctx, arch):
    tracker, feats, mf, model = ctx
    m = mf.train_model(feats, architecture=arch, dataset_key=DATASET_KEY, seed=7).model
    inf = _inf(tracker)
    asset = inf.predict(m, feats[1], train_feature_records=feats, dataset_key=DATASET_KEY).asset
    assert asset.status == InferenceStatus.GENERATED
    assert inf.integrity(asset).ok, inf.integrity(asset).to_dict()
    assert tracker.verify_chain(asset.lineage_id)
    assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
            "training_run", "model", "prediction"} <= {r.kind for r in tracker.chain(asset.lineage_id)}


def test_integrity_has_nine_checks(ctx):
    inf, asset = _predict(ctx)
    report = inf.integrity(asset)
    assert report.ok and report.to_dict()["n_checks"] == 9
    names = {c["name"] for c in report.to_dict()["checks"]}
    for expected in ("prediction_integrity", "confidence_integrity", "calibration_integrity",
                     "explanation_integrity", "determinism_integrity", "registry_integrity",
                     "audit_integrity", "lineage_integrity", "version_integrity"):
        assert expected in names


# ===========================================================================
# Registry (P5-I)
# ===========================================================================
def test_registry(ctx):
    tracker, feats, mf, model = ctx
    inf, asset = _predict(ctx)
    assert inf.registry.exists(asset.prediction_id)
    assert asset.prediction_id in inf.registry.by_model(asset.model_id)
    assert asset.prediction_id in inf.registry.by_feature(asset.feature_asset_id)
    assert asset.prediction_id in inf.registry.by_case(asset.case_id)
    assert asset.prediction_id in inf.registry.by_patient(asset.patient_id)
    rec = inf.registry.get(asset.prediction_id)
    with pytest.raises(ValueError):
        inf.registry.register(dataclasses.replace(rec, status=InferenceStatus.QUARANTINED))


# ===========================================================================
# Audit (P5-J)
# ===========================================================================
def test_audit(ctx):
    inf, asset = _predict(ctx)
    log = inf.audit_log_for(asset.prediction_id)
    assert log.verify() and log.head == asset.audit_head
    kinds = {e.kind for e in log.events()}
    assert {"model_loaded", "prediction_generated", "confidence_assessed", "calibration_assessed",
            "explanation_generated", "prediction_lineage_recorded", "prediction_registered"} <= kinds
    fresh = make_inference_audit_log()
    fresh.append("prediction_generated", {"a": 1})
    fresh.append("prediction_registered", {"b": 2})
    assert fresh.verify()
    fresh._events[0] = dataclasses.replace(fresh._events[0], payload={"a": 999})
    assert fresh.verify() is False


# ===========================================================================
# Lineage (P5-J)
# ===========================================================================
def test_lineage_parents_model_and_feature(ctx):
    tracker, feats, mf, model = ctx
    inf, asset = _predict(ctx)
    node = tracker.get(asset.lineage_id)
    assert node.kind == "prediction"
    assert model.lineage_id in node.parents
    assert feats[0].lineage_id in node.parents


# ===========================================================================
# Reports (P5-L)
# ===========================================================================
def test_reports(ctx):
    inf, asset = _predict(ctx)
    r1 = inf.reports(asset)
    r2 = inf.reports(asset)
    assert set(r1) == {"prediction_report", "confidence_report", "calibration_report",
                       "explainability_report", "inference_report", "registry_report",
                       "audit_report", "lineage_report", "validation_report"}
    assert r1 == r2
    assert r1["validation_report"]["ok"] is True
    assert r1["lineage_report"]["chain_verified"] is True


# ===========================================================================
# Determinism (P5)
# ===========================================================================
def test_determinism(ctx):
    tracker, feats, mf, model = ctx
    inf = _inf(tracker)
    a = inf.predict(model, feats[2], train_feature_records=feats, dataset_key=DATASET_KEY).asset
    b = inf.predict(model, feats[2], train_feature_records=feats, dataset_key=DATASET_KEY).asset
    assert a.prediction_id == b.prediction_id
    assert a.version.version == b.version.version
    assert a.prediction.signature() == b.prediction.signature()


# ===========================================================================
# Identity
# ===========================================================================
def test_identity():
    a = mint_identity("prediction", {"model_id": "model+" + "a" * 16, "prediction_key": "k1"})
    b = mint_identity("prediction", {"model_id": "model+" + "a" * 16, "prediction_key": "k1"})
    assert a.id == b.id and a.id.startswith("prediction+")
    assert a.derived_from == "model+" + "a" * 16
    with pytest.raises(IdentityError):
        mint_identity("prediction", {"model_id": "not-a-model", "prediction_key": "k"})
    assert validate_identity("prediction+" + "a" * 16, "prediction")[0] is True


# ===========================================================================
# Schemas
# ===========================================================================
def test_schemas(ctx):
    inf, asset = _predict(ctx)
    for name, payload in [
        ("InferenceRecord", asset.to_dict()),
        ("PredictionRecord", asset.prediction.to_dict()),
        ("ConfidenceRecord", asset.confidence.to_dict()),
        ("CalibrationRecord", asset.calibration.to_dict()),
        ("ExplanationRecord", asset.explanation.to_dict()),
        ("InferenceRegistryRecord", inf.registry.get(asset.prediction_id).to_dict()),
    ]:
        ok, missing = validate_entity(name, payload)
        assert ok, (name, missing)
    for entity in ["InferenceIdentity", "PredictionRecord", "PredictionClass", "ConfidenceRecord",
                   "CalibrationRecord", "ExplanationRecord", "InferenceValidationRecord",
                   "InferenceRegistryRecord", "InferenceAuditRecord", "InferenceLineageRecord",
                   "InferenceRecord"]:
        assert entity in ENTITY_CONTRACTS


# ===========================================================================
# Edge cases
# ===========================================================================
def test_predict_on_held_out_feature(ctx):
    """Predicting on a recording's feature asset still traces to its own patient."""
    tracker, feats, mf, model = ctx
    inf = _inf(tracker)
    asset = inf.predict(model, feats[5], train_feature_records=feats, dataset_key=DATASET_KEY).asset
    assert asset.patient_id == feats[5].patient_id
    assert tracker.verify_chain(asset.lineage_id)


def test_confidence_engine_unit():
    from backend.model_foundation.training import build_model
    X = np.array([[0.1, 0.2, 0.3], [0.9, 0.8, 0.7], [0.2, 0.1, 0.0], [0.8, 0.9, 1.0]])
    y = np.array([0, 1, 0, 1])
    model = build_model(ModelArchitecture.EEGNET, 2, seed=3).fit(X, y)
    probs = model.predict_proba(X[:1])[0]
    rec = ConfidenceEngine().assess(model, X[0], probs, n_classes=2)
    assert 0.0 <= rec.prediction_stability <= 1.0
    rec2 = ConfidenceEngine().assess(model, X[0], probs, n_classes=2)
    assert rec.signature() == rec2.signature()   # deterministic


# ===========================================================================
# Boundary
# ===========================================================================
def test_inference_foundation_respects_boundaries():
    root = REPO_ROOT / "backend" / "inference_foundation"
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
    assert uses_numpy, "inference foundation must use real numerics (numpy)"
