"""Shared helpers for the DRP-4 Persistence Platform tests.

Builds a real cohort (P1->P3), trains a real model (DRP-2/model-foundation), serves a real
prediction (DRP-3), and assembles a ``PlatformState`` to persist — all on one shared lineage
tracker (no replacement systems).
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService
from backend.model_foundation import ModelFoundationService, ModelArchitecture
from backend.serving_platform import ServingPlatformService, PredictionRequestContract
from backend.persistence_platform import PlatformState, RepositoryKind

import _eeg_fixtures as fx

FIXTURES = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def build_platform_state(eeg_fixtures, tmp_path, *, architecture=ModelArchitecture.EEGNET):
    """Run the real P1->P3->train->serve pipeline; return (tracker, services, PlatformState)."""
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

    mf = ModelFoundationService(lineage_tracker=tracker)
    serv = ServingPlatformService(lineage_tracker=tracker)
    model = mf.train_model(feats, architecture=architecture, dataset_key="cohort", seed=7).model
    serv.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(model_ref={"model_id": model.model_id},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = serv.serve(req, feats[0])

    state = PlatformState(
        lineage=tracker,
        registries={"model_registry": mf.model_registry, "dataset_registry": mf.dataset_registry,
                    "serving_registry": serv.registry},
        audit_logs={"serving": serv.audit_log_for(out.execution.execution_id)},
        execution_history={"serving": [out.execution.to_dict()],
                           "inference": [out.execution.response.to_dict()]},
        repositories={RepositoryKind.MODEL: {model.model_id: model.to_dict()},
                      RepositoryKind.SERVING: {out.execution.execution_id: out.execution.to_dict()}},
        anchor_lineage_id=out.execution.response.lineage_id)
    return tracker, {"mf": mf, "serv": serv, "model": model, "out": out}, state
