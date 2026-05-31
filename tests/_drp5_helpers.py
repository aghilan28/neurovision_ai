"""Shared helpers for the DRP-5 Security Platform tests.

Provides a security service seeded with users + credentials, and a helper that produces a
**real** DRP-3 serving resource (execution id + lineage node) so access control can be
exercised against real serving / persistence resources (no replacement systems).
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.security_platform import SecurityPlatformService, Role


def build_security_service(tracker=None):
    """A security service with a standard set of users + credentials + default policies."""
    svc = SecurityPlatformService(lineage_tracker=tracker or LineageTracker())
    svc.register_user("admin", Role.ADMIN)
    svc.register_user("erin", Role.ENGINEER)
    svc.register_user("rita", Role.RESEARCHER)
    svc.register_user("svc", Role.SERVICE)
    svc.register_user("aud", Role.AUDITOR)
    for name in ("admin", "erin", "rita", "svc", "aud"):
        svc.set_credential(name, f"pw-{name}-123")
    return svc


def build_real_serving_resource(eeg_fixtures, tmp_path, tracker):
    """Run the real P1->P3->train->serve pipeline on ``tracker``; return (execution_id,
    lineage_id) of a served execution to use as a SERVING resource."""
    from backend.clinical_cases import CaseService
    from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
    from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
    from backend.feature_engineering import FeatureEngineeringService
    from backend.model_foundation import ModelFoundationService, ModelArchitecture
    from backend.serving_platform import ServingPlatformService, PredictionRequestContract
    import _eeg_fixtures as fx

    cases = CaseService(lineage_tracker=tracker)
    es = LocalEEGStore(str(tmp_path / "raw"))
    esvc = EEGFoundationService(es, lineage_tracker=tracker)
    ps = ProcessedSignalStore(str(tmp_path / "proc"))
    ssvc = SignalProcessingService(es, ps, lineage_tracker=tracker)
    fsvc = FeatureEngineeringService(ps, lineage_tracker=tracker)
    feats = []
    for i, name in enumerate([fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS,
                              fx.VALID_FIF, fx.VALID_SET]):
        c = cases.create_case(patient_key=f"P-{i}", case_key=f"C-{i}")
        raw = esvc.ingest_eeg(eeg_fixtures[name], case_id=c.case_id, patient_id=c.patient_id,
                              case_lineage_id=c.lineage_id).asset
        feats.append(fsvc.generate_features(ssvc.process(raw).asset).asset)
    mf = ModelFoundationService(lineage_tracker=tracker)
    serv = ServingPlatformService(lineage_tracker=tracker)
    model = mf.train_model(feats, architecture=ModelArchitecture.EEGNET, dataset_key="cohort",
                           seed=7).model
    serv.load_model(model, feats, dataset_key="cohort")
    req = PredictionRequestContract(model_ref={"model_id": model.model_id},
                                    feature_asset_id=feats[0].feature_asset_id,
                                    case_id=feats[0].case_id, patient_id=feats[0].patient_id)
    out = serv.serve(req, feats[0])
    return out.execution.execution_id, out.execution.lineage_id
