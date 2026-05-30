"""Tests for the Signal Processing Foundation (Productization P2).

Covers every mandated category: filtering (bandpass, notch, ...), quality, artifact
detection, artifact removal, registry, audit, lineage, reports, boundaries,
corrupted inputs, and edge cases. Operates on the **real P1 EEG fixtures**
(EDF/EDF+/BDF/BDF+/FIF/SET); artifact edge cases are exercised by injecting artifacts
into arrays loaded from those real fixtures (no synthetic replacement fixtures).
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
from backend.signal_processing import (
    SignalProcessingService, ProcessedSignalStore, FilteringEngine, FilteringError,
    SignalQualityEngine, ArtifactDetectionEngine, ArtifactRemovalEngine, ArtifactType,
    ArtifactSeverity, ProcessedAssetStatus, QualityGrade, SignalKind, load_raw_signal,
    make_signal_audit_log, mint_identity, validate_identity, IdentityError,
)
from backend.signal_processing.schemas import ENTITY_CONTRACTS, validate_entity

import _eeg_fixtures as fx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
FAMILY = {fx.VALID_EDF: "EDF", fx.VALID_EDF_PLUS: "EDF", fx.VALID_BDF: "BDF",
          fx.VALID_BDF_PLUS: "BDF", fx.VALID_FIF: "FIF", fx.VALID_SET: "SET"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _env(tmp_path):
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
    eeg_store = LocalEEGStore(str(tmp_path / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    sig_svc = SignalProcessingService(eeg_store, ProcessedSignalStore(str(tmp_path / "proc")),
                                      lineage_tracker=tracker)
    return tracker, case, eeg_svc, sig_svc


def _ingest(eeg_svc, case, path):
    return eeg_svc.ingest_eeg(path, case_id=case.case_id, patient_id=case.patient_id,
                              case_lineage_id=case.lineage_id).asset


def _base_array(eeg_fixtures):
    """A real signal array loaded from the FIF fixture (distinct per-channel freqs)."""
    data, sfreq, ch = load_raw_signal(eeg_fixtures[fx.VALID_FIF], "FIF")
    return data.copy(), sfreq, ch


def _band_power(x, sfreq, lo, hi):
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sfreq)
    return float(spec[(freqs >= lo) & (freqs < hi)].sum())


# ===========================================================================
# Filtering (P2-C) — bandpass, notch, etc.
# ===========================================================================
def test_filter_bandpass_attenuates_out_of_band(eeg_fixtures):
    data, sfreq, _ = _base_array(eeg_fixtures)
    t = np.arange(data.shape[1]) / sfreq
    data[0] += 10.0 * np.sin(2 * np.pi * 60.0 * t)   # add 60 Hz component
    out, cfg = FilteringEngine().bandpass(data, sfreq, 0.5, 40.0)
    assert cfg.filter_type.value == "bandpass"
    before = _band_power(data[0], sfreq, 55, 65)
    after = _band_power(out[0], sfreq, 55, 65)
    assert after < 0.05 * before                      # 60 Hz strongly attenuated


def test_filter_notch_attenuates_line(eeg_fixtures):
    data, sfreq, _ = _base_array(eeg_fixtures)
    t = np.arange(data.shape[1]) / sfreq
    data[1] += 8.0 * np.sin(2 * np.pi * 60.0 * t)
    out, _ = FilteringEngine().notch(data, sfreq, 60.0)
    assert _band_power(out[1], sfreq, 59, 61) < 0.2 * _band_power(data[1], sfreq, 59, 61)


def test_filter_deterministic_and_non_mutating(eeg_fixtures):
    data, sfreq, _ = _base_array(eeg_fixtures)
    original = data.copy()
    a, _ = FilteringEngine().bandpass(data, sfreq, 0.5, 40.0)
    b, _ = FilteringEngine().bandpass(data, sfreq, 0.5, 40.0)
    assert np.array_equal(a, b)                       # deterministic
    assert np.array_equal(data, original)             # input never mutated


def test_filter_highpass_lowpass_reference(eeg_fixtures):
    data, sfreq, _ = _base_array(eeg_fixtures)
    hp, _ = FilteringEngine().highpass(data, sfreq, 1.0)
    lp, _ = FilteringEngine().lowpass(data, sfreq, 40.0)
    ref, cfg = FilteringEngine().reference(data, "average")
    assert hp.shape == data.shape and lp.shape == data.shape
    assert np.allclose(ref.mean(axis=0), 0.0, atol=1e-9)   # average reference removes common mean
    assert cfg.filter_type.value == "reference"


def test_filter_rejects_bad_parameters(eeg_fixtures):
    data, sfreq, _ = _base_array(eeg_fixtures)
    eng = FilteringEngine()
    with pytest.raises(FilteringError):
        eng.bandpass(data, sfreq, 40.0, 0.5)          # low >= high
    with pytest.raises(FilteringError):
        eng.lowpass(data, sfreq, sfreq)               # cutoff >= Nyquist


# ===========================================================================
# Quality (P2-D)
# ===========================================================================
def test_quality_on_real_fixture(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    q = SignalQualityEngine().assess(data, sfreq, ch, eeg_asset_id="eeg+" + "a" * 16,
                                     signal_kind=SignalKind.RAW)
    assert 0.0 <= q.recording_quality_score <= 1.0
    assert len(q.channel_qualities) == data.shape[0]
    assert q.grade in set(QualityGrade)
    assert q.sampling_consistency == 1.0


def test_quality_flags_flat_channel(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[0] = 0.0
    q = SignalQualityEngine().assess(data, sfreq, ch, eeg_asset_id="eeg+" + "a" * 16,
                                     signal_kind=SignalKind.RAW)
    assert q.channel_qualities[0].quality_score < 0.3
    assert any(f.code == "low_channel_quality" for f in q.findings)
    assert q.recommendations


def test_quality_deterministic(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    a = SignalQualityEngine().assess(data, sfreq, ch, eeg_asset_id="eeg+" + "a" * 16,
                                     signal_kind=SignalKind.RAW)
    b = SignalQualityEngine().assess(data, sfreq, ch, eeg_asset_id="eeg+" + "a" * 16,
                                     signal_kind=SignalKind.RAW)
    assert a.to_dict() == b.to_dict()


# ===========================================================================
# Artifact detection (P2-E)
# ===========================================================================
def test_detection_clean_no_structural_false_positives(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    arts = ArtifactDetectionEngine().detect_all(data, sfreq, ch)
    types = {a.artifact_type for a in arts}
    assert ArtifactType.FLAT_CHANNEL not in types
    assert ArtifactType.SATURATED_CHANNEL not in types


def test_detection_flat_channel(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[0] = 0.0
    arts = ArtifactDetectionEngine().detect_flat_channels(data, sfreq, ch)
    assert arts and arts[0].artifact_type == ArtifactType.FLAT_CHANNEL
    a = arts[0]
    assert a.severity == ArtifactSeverity.CRITICAL and 0.0 <= a.confidence <= 1.0
    assert ch[0] in a.affected_channels and a.duration_seconds > 0


def test_detection_saturated_channel(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    amax = np.max(np.abs(data[1]))
    data[1] = np.clip(data[1] * 100, -amax, amax)     # heavy clipping
    arts = ArtifactDetectionEngine().detect_saturated_channels(data, sfreq, ch)
    assert any(a.artifact_type == ArtifactType.SATURATED_CHANNEL for a in arts)


def test_detection_powerline(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    t = np.arange(data.shape[1]) / sfreq
    for i in range(data.shape[0]):
        data[i] += 50.0 * np.sin(2 * np.pi * 60.0 * t)
    arts = ArtifactDetectionEngine().detect_powerline(data, sfreq, ch)
    assert arts and arts[0].artifact_type == ArtifactType.POWERLINE
    assert arts[0].detail["line_hz"] == 60.0


def test_detection_emg(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    rng = np.random.default_rng(0)
    hf = rng.standard_normal(data.shape[1])
    # band-limit noise to >30 Hz so it reads as EMG
    hf_out, _ = FilteringEngine().highpass(hf[None, :], sfreq, 35.0)
    data[2] = 50.0 * hf_out[0]
    arts = ArtifactDetectionEngine().detect_emg(data, sfreq, ch)
    assert any(a.artifact_type == ArtifactType.EMG for a in arts)


def test_detection_channel_dropout(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[1, : data.shape[1] // 2] = 0.0               # half-channel dropout
    arts = ArtifactDetectionEngine().detect_channel_dropout(data, sfreq, ch)
    assert any(a.artifact_type == ArtifactType.CHANNEL_DROPOUT for a in arts)


def test_detection_deterministic(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[0] = 0.0
    e = ArtifactDetectionEngine()
    a = [r.to_dict() for r in e.detect_all(data, sfreq, ch)]
    b = [r.to_dict() for r in e.detect_all(data, sfreq, ch)]
    assert a == b


# ===========================================================================
# Artifact removal (P2-F)
# ===========================================================================
def test_removal_interpolation_repairs_nan(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[2, 5:10] = np.nan
    out, info = ArtifactRemovalEngine().interpolation(data)
    assert np.isfinite(out).all() and info["n_samples_repaired"] == 5


def test_removal_channel_repair(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    data[0] = 0.0
    out, info = ArtifactRemovalEngine().channel_repair(data, (0,))
    assert np.std(out[0]) > 0 and info["repaired_channels"] == [0]


def test_removal_ica_deterministic_and_non_mutating(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    original = data.copy()
    a, ia = ArtifactRemovalEngine().ica_remove(data, sfreq, ch)
    b, ib = ArtifactRemovalEngine().ica_remove(data, sfreq, ch)
    assert np.allclose(a, b)                          # deterministic
    assert a.shape == data.shape
    assert np.array_equal(data, original)             # input never mutated


def test_removal_adaptive_and_noise_suppression(eeg_fixtures):
    data, sfreq, ch = _base_array(eeg_fixtures)
    t = np.arange(data.shape[1]) / sfreq
    data[2] += 20.0 * np.sin(2 * np.pi * 60.0 * t)
    clean, info = ArtifactRemovalEngine().noise_suppression(data, sfreq, powerline_hz=60.0)
    assert _band_power(clean[2], sfreq, 59, 61) < _band_power(data[2], sfreq, 59, 61)
    out, info2 = ArtifactRemovalEngine().adaptive_filter(data, ch)
    assert out.shape == data.shape and "betas" in info2


# ===========================================================================
# Service: raw -> processed, status, determinism, raw immutability
# ===========================================================================
@pytest.mark.parametrize("name", VALID)
def test_process_all_formats(eeg_fixtures, tmp_path, name):
    tracker, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[name])
    out = sig_svc.process(raw)
    assert out.accepted, name
    asset = out.asset
    assert asset.status == ProcessedAssetStatus.PROCESSED
    assert asset.processed_signal.n_channels == raw.channel_set.count
    assert sig_svc.integrity(asset).ok, sig_svc.integrity(asset).to_dict()
    assert tracker.verify_chain(asset.lineage_id)
    assert {"patient", "case", "eeg", "processed_eeg"} <= {
        r.kind for r in tracker.chain(asset.lineage_id)}


def test_processing_traceability_chain(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_FIF])
    asset = sig_svc.process(raw).asset
    steps = asset.processing.steps
    assert steps[0].input_fingerprint == asset.processing.input_fingerprint
    for a, b in zip(steps, steps[1:]):
        assert a.output_fingerprint == b.input_fingerprint
    assert steps[-1].output_fingerprint == asset.processing.output_fingerprint
    assert asset.storage.content_fingerprint == asset.processing.output_fingerprint


def test_raw_eeg_immutability(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_EDF])
    asset = sig_svc.process(raw).asset
    # the raw store still verifies (untouched) and the processed store is separate
    assert eeg_svc.store.verify(raw.storage) is True
    assert sig_svc.processed_store.root_dir != eeg_svc.store.root_dir
    report = sig_svc.integrity(asset)
    assert report.ok is True   # includes the raw_immutability check


def test_processing_is_deterministic(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_SET])
    a = sig_svc.process(raw).asset
    b = sig_svc.process(raw).asset
    assert a.processed_id == b.processed_id
    assert a.version.version == b.version.version
    assert a.state_signature() == b.state_signature()


def test_unreadable_raw_is_rejected(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    # a corrupted EDF is ingested by P1 as a QUARANTINED asset (recognized, undecodable)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.CORRUPTED_EDF])
    out = sig_svc.process(raw)
    assert out.accepted is False
    assert out.asset is None
    assert out.reason.startswith("unreadable_raw")


def test_artifacted_signal_triggers_removal(eeg_fixtures, tmp_path, monkeypatch):
    """A signal with injected artifacts exercises detection-driven removal."""
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_FIF])

    real_load = load_raw_signal

    def fake_load(path, family):
        data, sfreq, ch = real_load(path, family)
        data = data.copy()
        data[0] = 0.0                                 # flat channel -> structural artifact
        return data, sfreq, ch

    monkeypatch.setattr("backend.signal_processing.service.load_raw_signal", fake_load)
    out = sig_svc.process(raw)
    assert out.accepted
    assert out.n_artifacts >= 1
    assert "channel_repair" in [m.value for m in out.asset.processing.removal_methods]
    assert out.asset.artifact_history.addressed_artifact_ids


# ===========================================================================
# Identity
# ===========================================================================
def test_identity_content_addressed():
    a = mint_identity("signal", {"eeg_asset_id": "eeg+" + "a" * 16, "processing_key": "k1"})
    b = mint_identity("signal", {"eeg_asset_id": "eeg+" + "a" * 16, "processing_key": "k1"})
    c = mint_identity("signal", {"eeg_asset_id": "eeg+" + "a" * 16, "processing_key": "k2"})
    assert a.id == b.id and a.id != c.id
    assert a.id.startswith("signal+") and a.derived_from == "eeg+" + "a" * 16
    with pytest.raises(IdentityError):
        mint_identity("signal", {"eeg_asset_id": "not-an-eeg", "processing_key": "k"})
    assert validate_identity("signal+" + "a" * 16, "signal")[0] is True


# ===========================================================================
# Registry / Audit / Lineage / Reports
# ===========================================================================
def test_registry_no_orphan_no_overwrite(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_EDF])
    asset = sig_svc.process(raw).asset
    assert sig_svc.registry.exists(asset.processed_id)
    assert asset.processed_id in sig_svc.registry.by_eeg_asset(raw.asset_id)
    assert asset.processed_id in sig_svc.registry.by_case(case.case_id)
    rec = sig_svc.registry.get(asset.processed_id)
    with pytest.raises(ValueError):
        sig_svc.registry.register(dataclasses.replace(rec, status=ProcessedAssetStatus.QUARANTINED))


def test_audit_trail_and_tamper_evidence(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_EDF])
    asset = sig_svc.process(raw).asset
    log = sig_svc.audit_log_for(asset.processed_id)
    assert log.verify() and log.head == asset.audit_head
    kinds = {e.kind for e in log.events()}
    assert {"signal_loaded", "quality_assessed_raw", "artifacts_detected", "signal_processed",
            "signal_stored", "signal_lineage_recorded", "signal_registered"} <= kinds

    fresh = make_signal_audit_log()
    fresh.append("signal_loaded", {"a": 1})
    fresh.append("signal_stored", {"b": 2})
    assert fresh.verify() is True
    fresh._events[0] = dataclasses.replace(fresh._events[0], payload={"a": 999})
    assert fresh.verify() is False


def test_lineage_node_parents_raw_eeg(eeg_fixtures, tmp_path):
    tracker, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_FIF])
    asset = sig_svc.process(raw).asset
    node = tracker.get(asset.lineage_id)
    assert raw.lineage_id in node.parents
    assert node.kind == "processed_eeg"


def test_reports_generated_and_deterministic(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_FIF])
    asset = sig_svc.process(raw).asset
    r1 = sig_svc.reports(asset)
    r2 = sig_svc.reports(asset)
    assert set(r1) == {"quality_report", "artifact_report", "filtering_report",
                       "processing_report", "registry_report", "audit_report", "lineage_report"}
    assert r1 == r2
    assert r1["lineage_report"]["chain_verified"] is True
    assert r1["registry_report"]["n_assets"] == 1


# ===========================================================================
# Schemas / contracts
# ===========================================================================
def test_entity_contracts(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc = _env(tmp_path)
    raw = _ingest(eeg_svc, case, eeg_fixtures[fx.VALID_SET])
    asset = sig_svc.process(raw).asset
    for name, payload in [
        ("ProcessedEEGRecord", asset.to_dict()),
        ("SignalQualityRecord", asset.quality.to_dict()),
        ("SignalProcessingRecord", asset.processing.to_dict()),
        ("ProcessedEEGStorageRecord", asset.storage.to_dict()),
        ("SignalRegistryRecord", sig_svc.registry.get(asset.processed_id).to_dict()),
    ]:
        ok, missing = validate_entity(name, payload)
        assert ok, (name, missing)
    for entity in ["SignalIdentity", "SignalRecord", "SignalQualityRecord",
                   "SignalArtifactRecord", "SignalProcessingRecord", "SignalRegistryRecord",
                   "SignalAuditRecord", "SignalLineageRecord", "ProcessedEEGRecord"]:
        assert entity in ENTITY_CONTRACTS


# ===========================================================================
# Edge cases
# ===========================================================================
def test_quality_and_detection_on_tiny_array():
    data = np.zeros((1, 4), dtype=float)
    q = SignalQualityEngine().assess(data, 256.0, ("c0",), eeg_asset_id="eeg+" + "a" * 16,
                                     signal_kind=SignalKind.RAW)
    assert 0.0 <= q.recording_quality_score <= 1.0
    arts = ArtifactDetectionEngine().detect_all(data, 256.0, ("c0",))
    assert any(a.artifact_type == ArtifactType.FLAT_CHANNEL for a in arts)


def test_filtering_handles_short_signal():
    data = np.sin(np.linspace(0, 6.28, 32))[None, :].repeat(2, axis=0)
    out, _ = FilteringEngine().bandpass(data, 64.0, 0.5, 20.0)
    assert out.shape == data.shape and np.isfinite(out).all()


# ===========================================================================
# Boundary
# ===========================================================================
def test_signal_processing_respects_boundaries():
    root = REPO_ROOT / "backend" / "signal_processing"
    forbidden = {"frontend", "tests", "scripts", "tools", "monitoring", "deployment"}
    uses_scipy = uses_mne = False
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            roots = []
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                roots = [node.module.split(".")[0]]
            assert not (set(roots) & forbidden), f"{path} imports forbidden module {roots}"
            uses_scipy = uses_scipy or "scipy" in roots
            uses_mne = uses_mne or "mne" in roots
    assert uses_scipy, "filtering must use real DSP (scipy)"
    assert uses_mne, "raw-signal loading must use the real reader (mne)"
