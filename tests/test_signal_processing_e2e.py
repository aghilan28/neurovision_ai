"""End-to-end test for Productization P2 — Signal Processing Foundation.

Demonstrates the full required deliverable: a real EEG file enters the platform (P1),
is loaded, quality-assessed, artifact-detected, cleaned, stored, tracked, audited, and
traced into a processed-EEG asset whose chain verifies Patient -> Case -> EEG ->
Processed — across all six supported formats — with the raw EEG left immutable.
"""

from __future__ import annotations


from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
from backend.signal_processing import (
    SignalProcessingService, ProcessedSignalStore, ProcessedAssetStatus,
)

import _eeg_fixtures as fx

VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _platform(tmp_path):
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-100", case_key="C-100")
    eeg_store = LocalEEGStore(str(tmp_path / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    sig_svc = SignalProcessingService(eeg_store, ProcessedSignalStore(str(tmp_path / "proc")),
                                      lineage_tracker=tracker)
    return tracker, case, eeg_svc, sig_svc


def test_raw_to_clean_for_every_format(eeg_fixtures, tmp_path):
    tracker, case, eeg_svc, sig_svc = _platform(tmp_path)
    for name in VALID:
        raw = eeg_svc.ingest_eeg(eeg_fixtures[name], case_id=case.case_id,
                                 patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
        out = sig_svc.process(raw)
        assert out.accepted, name
        a = out.asset
        # loaded + quality-assessed (before & after) + cleaned
        assert a.quality_history.before is not None and a.quality_history.after is not None
        assert a.processed_signal.n_channels == raw.channel_set.count
        assert a.metadata.applied_filters                      # filtering happened
        # stored (separate store) + raw untouched
        assert sig_svc.processed_store.verify(a.storage) is True
        assert eeg_svc.store.verify(raw.storage) is True
        # registered + audited + integrity
        assert a.status == ProcessedAssetStatus.PROCESSED
        assert sig_svc.registry.exists(a.processed_id)
        assert sig_svc.audit_log_for(a.processed_id).verify() is True
        assert sig_svc.integrity(a).ok is True
        # traced: Patient -> Case -> EEG -> Processed
        assert tracker.verify_chain(a.lineage_id) is True
        assert {"patient", "case", "eeg", "processed_eeg"} <= {
            r.kind for r in tracker.chain(a.lineage_id)}

    assert len(sig_svc.registry.list_assets()) == 6


def test_one_case_many_recordings_share_lineage_root(eeg_fixtures, tmp_path):
    tracker, case, eeg_svc, sig_svc = _platform(tmp_path)
    processed_ids = []
    for name in (fx.VALID_EDF, fx.VALID_FIF, fx.VALID_SET):
        raw = eeg_svc.ingest_eeg(eeg_fixtures[name], case_id=case.case_id,
                                 patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
        processed_ids.append(sig_svc.process(raw).asset.processed_id)
    assert len(set(processed_ids)) == 3
    assert len(sig_svc.registry.by_case(case.case_id)) == 3
    assert len(sig_svc.registry.by_patient(case.patient_id)) == 3


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker = LineageTracker()
        case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
        es = LocalEEGStore(str(tmp_path / sub / "raw"))
        esvc = EEGFoundationService(es, lineage_tracker=tracker)
        ssvc = SignalProcessingService(es, ProcessedSignalStore(str(tmp_path / sub / "proc")),
                                       lineage_tracker=tracker)
        raw = esvc.ingest_eeg(eeg_fixtures[fx.VALID_FIF], case_id=case.case_id,
                              patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
        return ssvc.process(raw).asset

    a, b = run("a"), run("b")
    assert a.processed_id == b.processed_id
    assert a.version.version == b.version.version
    assert a.processing.output_fingerprint == b.processing.output_fingerprint
