"""End-to-end test for Productization P4 — Model Foundation Platform.

Demonstrates the full required deliverable: a real EEG file enters the platform (P1),
is cleaned (P2), feature-engineered (P3), assembled into a patient-disjoint dataset,
used to train + evaluate + register a validated model whose chain verifies
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model.
"""

from __future__ import annotations

import dataclasses

import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture, ModelStatus

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


def test_full_pipeline_trains_every_architecture(eeg_fixtures, tmp_path):
    tracker, feats = _cohort(eeg_fixtures, tmp_path)
    mf = ModelFoundationService(lineage_tracker=tracker)
    for arch in ModelArchitecture:
        out = mf.train_model(feats, architecture=arch, name=f"exp-{arch.value}",
                             dataset_key="cohort", seed=7)
        assert out.accepted
        m = out.model
        assert m.status == ModelStatus.TRAINED
        assert mf.model_registry.exists(m.model_id)
        assert mf.experiment_registry.exists(m.experiment_id)
        assert mf.dataset_registry.exists(m.dataset_id)
        assert mf.integrity(m).ok
        assert tracker.verify_chain(m.lineage_id)
        assert {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                "training_run", "model"} <= {r.kind for r in tracker.chain(m.lineage_id)}
        # the model is immutable
        with pytest.raises(dataclasses.FrozenInstanceError):
            m.status = ModelStatus.QUARANTINED

    assert len(mf.model_registry.list_models()) == len(list(ModelArchitecture))
    # all four models trained on a single shared, patient-disjoint dataset
    assert len(mf.dataset_registry.list_datasets()) == 1


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker, feats = _cohort(eeg_fixtures, tmp_path / sub)
        mf = ModelFoundationService(lineage_tracker=tracker)
        return mf.train_model(feats, architecture=ModelArchitecture.DEEPCONVNET,
                              dataset_key="cohort", seed=7).model

    a, b = run("a"), run("b")
    assert a.model_id == b.model_id
    assert a.version.version == b.version.version
    assert a.params_fingerprint == b.params_fingerprint
    assert a.metadata.signature() == b.metadata.signature()
