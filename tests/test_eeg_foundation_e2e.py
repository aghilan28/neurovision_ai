"""End-to-end test for Productization P1 — Real EEG Foundation.

Demonstrates the full required deliverable: a real EEG file enters the platform
under a clinical Case and becomes a tracked, traceable NeuroVision EEG asset, with
the chain Patient -> Case -> EEG verifying end to end — across all six supported
formats, plus the quarantine (corrupted) and reject (unsupported) paths.
"""

from __future__ import annotations

import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import EEGFoundationService, LocalEEGStore, EEGAssetStatus

import _eeg_fixtures as fx

VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _platform(tmp_path):
    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    case = cases.create_case(patient_key="P-100", case_key="C-100")
    svc = EEGFoundationService(LocalEEGStore(str(tmp_path / "store")), lineage_tracker=tracker)
    return tracker, case, svc


def test_real_eeg_file_enters_platform_for_every_format(eeg_fixtures, tmp_path):
    tracker, case, svc = _platform(tmp_path)
    for name in VALID:
        out = svc.ingest_eeg(eeg_fixtures[name], case_id=case.case_id,
                             patient_id=case.patient_id, case_lineage_id=case.lineage_id)
        assert out.accepted, name
        asset = out.asset
        # loaded + parsed + understood
        assert asset.eeg_format.value == name_to_format(name)
        assert asset.channel_set.count == 3
        assert asset.metadata.sampling_frequency == 256.0
        assert asset.metadata.duration_seconds == pytest.approx(2.0)
        # validated + registered
        assert asset.status == EEGAssetStatus.REGISTERED
        assert svc.registry.exists(asset.asset_id)
        # stored
        assert svc.store.verify(asset.storage) is True
        # traced: Patient -> Case -> EEG
        assert tracker.verify_chain(asset.lineage_id) is True
        chain_kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        assert {"patient", "case", "eeg"} <= chain_kinds
        # audited
        assert svc.audit_log_for(asset.asset_id).verify() is True
        # integrity
        assert svc.integrity(asset).ok is True

    # one case now carries six distinct EEG assets
    assert len(svc.registry.by_case(case.case_id)) == 6
    assert len(svc.registry.by_patient(case.patient_id)) == 6


def test_quarantine_and_reject_paths(eeg_fixtures, tmp_path):
    tracker, case, svc = _platform(tmp_path)

    corrupt = svc.ingest_eeg(eeg_fixtures[fx.CORRUPTED_BDF], case_id=case.case_id,
                             patient_id=case.patient_id, case_lineage_id=case.lineage_id)
    assert corrupt.accepted and corrupt.asset.status == EEGAssetStatus.QUARANTINED
    assert tracker.verify_chain(corrupt.asset.lineage_id) is True  # still fully traced

    rejected = svc.ingest_eeg(eeg_fixtures[fx.UNSUPPORTED], case_id=case.case_id,
                              patient_id=case.patient_id, case_lineage_id=case.lineage_id)
    assert rejected.accepted is False and rejected.asset is None


def test_cross_run_determinism(eeg_fixtures, tmp_path):
    """Same file + same case keys -> identical asset id, version, and signatures."""
    def run(sub):
        tracker = LineageTracker()
        case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
        svc = EEGFoundationService(LocalEEGStore(str(tmp_path / sub)), lineage_tracker=tracker)
        return svc.ingest_eeg(eeg_fixtures[fx.VALID_EDF], case_id=case.case_id,
                              patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset

    a, b = run("a"), run("b")
    assert a.asset_id == b.asset_id
    assert a.version.version == b.version.version
    assert a.metadata.signature() == b.metadata.signature()
    assert a.state_signature() == b.state_signature()


def name_to_format(name: str) -> str:
    return {
        fx.VALID_EDF: "EDF", fx.VALID_EDF_PLUS: "EDF+", fx.VALID_BDF: "BDF",
        fx.VALID_BDF_PLUS: "BDF+", fx.VALID_FIF: "FIF", fx.VALID_SET: "SET",
    }[name]
