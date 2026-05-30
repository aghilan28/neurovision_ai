"""End-to-end test for Productization P5 — Clinical Inference Foundation.

Demonstrates the full required deliverable: a real EEG file enters the platform (P1),
is cleaned (P2), feature-engineered (P3), used to train a model (P4), and then a
validated prediction (+ confidence + calibration + explanation) is generated, whose
chain verifies
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model -> Prediction.
"""

from __future__ import annotations

import dataclasses

import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture
from backend.inference_foundation import InferenceFoundationService, InferenceStatus

import _eeg_fixtures as fx

FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _cohort(eeg_fixtures, tmp_path):
    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    es = LocalEEGStore(str(tmp_path / "raw"))
    esvc = EEGFoundationService(es, lineage_tracker=tracker)
    ps = ProcessedSignalStore(str(tmp_path / "proc"))
    ssvc = SignalProcessingService(es, ps, lineage_tracker=tracker)
    fsvc = FeatureEngineeringService(ps, lineage_tracker=tracker)
    feats = []
    for i, name in enumerate(FIXTURES):
        c = cases.create_case(patient_key=f"P-{i}", case_key=f"C-{i}")
        raw = esvc.ingest_eeg(eeg_fixtures[name], case_id=c.case_id, patient_id=c.patient_id,
                              case_lineage_id=c.lineage_id).asset
        feats.append(fsvc.generate_features(ssvc.process(raw).asset).asset)
    return tracker, feats


def test_full_pipeline_predicts_for_every_architecture(eeg_fixtures, tmp_path):
    tracker, feats = _cohort(eeg_fixtures, tmp_path)
    mf = ModelFoundationService(lineage_tracker=tracker)
    inf = InferenceFoundationService(lineage_tracker=tracker)
    for arch in ModelArchitecture:
        model = mf.train_model(feats, architecture=arch, dataset_key="cohort", seed=7).model
        out = inf.predict(model, feats[0], train_feature_records=feats, dataset_key="cohort")
        assert out.accepted
        a = out.asset
        assert a.status == InferenceStatus.GENERATED
        # prediction + confidence + calibration + explanation all present
        assert len(a.prediction.classes) == model.metadata.n_classes
        assert a.confidence.confidence_level is not None
        assert a.calibration.calibration_quality is not None
        assert len(a.explanation.feature_contributions) == 29
        # registered + audited + integrity
        assert inf.registry.exists(a.prediction_id)
        assert inf.audit_log_for(a.prediction_id).verify()
        assert inf.integrity(a).ok
        # traced: Patient -> ... -> Model -> Prediction
        assert tracker.verify_chain(a.lineage_id)
        assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                "training_run", "model", "prediction"} <= {r.kind for r in tracker.chain(a.lineage_id)}
        # the prediction asset is immutable
        with pytest.raises(dataclasses.FrozenInstanceError):
            a.status = InferenceStatus.QUARANTINED


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker, feats = _cohort(eeg_fixtures, tmp_path / sub)
        mf = ModelFoundationService(lineage_tracker=tracker)
        inf = InferenceFoundationService(lineage_tracker=tracker)
        model = mf.train_model(feats, architecture=ModelArchitecture.DEEPCONVNET,
                               dataset_key="cohort", seed=7).model
        return inf.predict(model, feats[0], train_feature_records=feats, dataset_key="cohort").asset

    a, b = run("a"), run("b")
    assert a.prediction_id == b.prediction_id
    assert a.version.version == b.version.version
    assert a.prediction.signature() == b.prediction.signature()
    assert a.confidence.signature() == b.confidence.signature()
