"""Shared helpers for the DRP-3 Serving Platform tests.

Builds a real cohort of P3 feature assets through the genuine P1 -> P2 -> P3 pipeline over
the committed EEG fixtures (no replacement systems), on one shared lineage tracker, and
trains a real model-foundation model to serve.
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture

import _eeg_fixtures as fx

FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def build_feature_cohort(eeg_fixtures, tmp_path):
    """Run P1 -> P2 -> P3 over the fixtures; return (shared_tracker, [FeatureRecord])."""
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


def train_model(tracker, feats, *, architecture=ModelArchitecture.EEGNET, dataset_key="cohort",
                seed=7):
    """Train a real model-foundation model on the shared tracker (the servable artifact)."""
    mf = ModelFoundationService(lineage_tracker=tracker)
    return mf.train_model(feats, architecture=architecture, dataset_key=dataset_key, seed=seed).model
