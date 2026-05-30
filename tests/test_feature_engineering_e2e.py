"""End-to-end test for Productization P3 — Feature Engineering Platform.

Demonstrates the full required deliverable: a real EEG file enters the platform (P1),
is cleaned (P2), and has features generated into an immutable feature asset whose
chain verifies Patient -> Case -> EEG -> Processed -> Feature — across all six
supported formats.
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
from backend.feature_engineering import FeatureEngineeringService, FeatureFamily, FeatureAssetStatus

import _eeg_fixtures as fx

VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _platform(tmp_path):
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-100", case_key="C-100")
    eeg_store = LocalEEGStore(str(tmp_path / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    proc_store = ProcessedSignalStore(str(tmp_path / "proc"))
    sig_svc = SignalProcessingService(eeg_store, proc_store, lineage_tracker=tracker)
    feat_svc = FeatureEngineeringService(proc_store, lineage_tracker=tracker)
    return tracker, case, eeg_svc, sig_svc, feat_svc


def test_full_pipeline_for_every_format(eeg_fixtures, tmp_path):
    tracker, case, eeg_svc, sig_svc, feat_svc = _platform(tmp_path)
    for name in VALID:
        raw = eeg_svc.ingest_eeg(eeg_fixtures[name], case_id=case.case_id,
                                 patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
        processed = sig_svc.process(raw).asset
        out = feat_svc.generate_features(processed)
        assert out.accepted, name
        a = out.asset
        # five families generated, validated, immutable, registered
        assert set(a.families) == {f.value for f in FeatureFamily}
        assert a.status == FeatureAssetStatus.GENERATED
        assert a.validation.ok
        assert feat_svc.registry.exists(a.feature_asset_id)
        assert feat_svc.audit_log_for(a.feature_asset_id).verify()
        assert feat_svc.integrity(a).ok
        # traced: Patient -> Case -> EEG -> Processed -> Feature
        assert tracker.verify_chain(a.lineage_id)
        assert {"patient", "case", "eeg", "processed_eeg", "feature"} <= {
            r.kind for r in tracker.chain(a.lineage_id)}
        # immutability: FeatureRecord is frozen
        import dataclasses
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            a.status = FeatureAssetStatus.QUARANTINED

    assert len(feat_svc.registry.list_assets()) == 6


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker = LineageTracker()
        case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
        es = LocalEEGStore(str(tmp_path / sub / "raw"))
        esvc = EEGFoundationService(es, lineage_tracker=tracker)
        ps = ProcessedSignalStore(str(tmp_path / sub / "proc"))
        ssvc = SignalProcessingService(es, ps, lineage_tracker=tracker)
        fsvc = FeatureEngineeringService(ps, lineage_tracker=tracker)
        raw = esvc.ingest_eeg(eeg_fixtures[fx.VALID_FIF], case_id=case.case_id,
                              patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
        proc = ssvc.process(raw).asset
        return fsvc.generate_features(proc).asset

    a, b = run("a"), run("b")
    assert a.feature_asset_id == b.feature_asset_id
    assert a.version.version == b.version.version
    assert a.metadata.signature() == b.metadata.signature()
