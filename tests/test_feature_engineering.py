"""Tests for the Feature Engineering Platform (Productization P3).

Covers every mandated category: frequency, temporal, connectivity, spectral, and
topography features; registry; audit; lineage; validation; reports; boundaries;
determinism; and edge cases. Runs the real P1 ingest -> P2 process -> P3 features
pipeline over the committed P1 EEG fixtures (no replacement systems).
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
from backend.feature_engineering import (
    FeatureEngineeringService, FrequencyFeatureEngine, TemporalFeatureEngine,
    ConnectivityFeatureEngine, SpectralRepresentationEngine, TopographyRepresentationEngine,
    FeatureContentValidator, load_processed_signal, FeatureFamily, FeatureGroup, FeatureScope,
    FeatureVector, FeatureAssetStatus, mint_identity, validate_identity, IdentityError,
    make_feature_audit_log,
)
from backend.feature_engineering._common import REGION_NAMES
from backend.feature_engineering.schemas import ENTITY_CONTRACTS, validate_entity

import _eeg_fixtures as fx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]


def _pipeline(tmp_path):
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-1", case_key="C-1")
    eeg_store = LocalEEGStore(str(tmp_path / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    proc_store = ProcessedSignalStore(str(tmp_path / "proc"))
    sig_svc = SignalProcessingService(eeg_store, proc_store, lineage_tracker=tracker)
    feat_svc = FeatureEngineeringService(proc_store, lineage_tracker=tracker)
    return tracker, case, eeg_svc, sig_svc, feat_svc


def _processed(eeg_svc, sig_svc, case, path):
    raw = eeg_svc.ingest_eeg(path, case_id=case.case_id, patient_id=case.patient_id,
                             case_lineage_id=case.lineage_id).asset
    return sig_svc.process(raw).asset


def _array(feat_svc, processed):
    return load_processed_signal(feat_svc.processed_store, processed)


# ===========================================================================
# Frequency features (P3-C)
# ===========================================================================
def test_frequency_features(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    vectors = FrequencyFeatureEngine().extract(data, sfreq, ch)
    names = {v.name for v in vectors}
    for b in ("delta", "theta", "alpha", "beta", "gamma"):
        assert f"abs_power_{b}" in names and f"rel_power_{b}" in names
    assert {"absolute_power", "spectral_entropy"} <= names
    assert any(v.group == FeatureGroup.BAND_RATIO for v in vectors)
    for v in vectors:
        assert v.family == FeatureFamily.FREQUENCY
        if v.scope == FeatureScope.PER_CHANNEL:
            assert v.n_values == data.shape[0]
    rel = next(v for v in vectors if v.name == "rel_power_alpha")
    assert all(0.0 <= x <= 1.001 for x in rel.values)


# ===========================================================================
# Temporal features (P3-D)
# ===========================================================================
def test_temporal_features(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    vectors = TemporalFeatureEngine().extract(data, sfreq, ch)
    names = {v.name for v in vectors}
    assert {"mean", "variance", "skewness", "kurtosis", "rms", "zero_crossing_rate",
            "hjorth_activity", "hjorth_mobility", "hjorth_complexity", "signal_entropy"} <= names
    per_ch = [v for v in vectors if v.scope == FeatureScope.PER_CHANNEL]
    assert all(v.n_values == data.shape[0] for v in per_ch)
    assert any(v.scope == FeatureScope.PER_RECORDING for v in vectors)   # per-recording summary


# ===========================================================================
# Connectivity features (P3-E)
# ===========================================================================
def test_connectivity_features(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    n = data.shape[0]
    vectors = {v.name: v for v in ConnectivityFeatureEngine().extract(data, sfreq, ch)}
    for name in ("coherence_matrix", "plv_matrix", "cross_correlation_matrix"):
        v = vectors[name]
        assert v.shape == (n, n) and v.n_values == n * n
        m = np.array(v.values).reshape(n, n)
        assert np.allclose(np.diag(m), 1.0)               # self-connectivity = 1
        assert np.allclose(m, m.T, atol=1e-6)             # symmetric
    coh = np.array(vectors["coherence_matrix"].values)
    assert np.all((coh >= -1e-9) & (coh <= 1.0 + 1e-6))
    assert "synchronization" in vectors


# ===========================================================================
# Spectral representations (P3-F)
# ===========================================================================
def test_spectral_representations(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    n = data.shape[0]
    vectors = {v.name: v for v in SpectralRepresentationEngine().extract(data, sfreq, ch)}
    assert vectors["psd"].shape[0] == n and len(vectors["psd"].shape) == 2
    assert len(vectors["spectrogram"].shape) == 3 and vectors["spectrogram"].shape[0] == n
    assert vectors["band_summary"].n_values == 5
    hist = np.array(vectors["frequency_histogram"].values)
    assert abs(hist.sum() - 1.0) < 1e-6


# ===========================================================================
# Topography representations (P3-G)
# ===========================================================================
def test_topography_representations(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    vectors = {v.name: v for v in TopographyRepresentationEngine().extract(data, sfreq, ch)}
    assert vectors["channel_layout"].n_values == data.shape[0]
    assert vectors["regional_rms"].n_values == len(REGION_NAMES)
    assert "spatial_summary" in vectors and "topographic_stat" in vectors
    # structured numeric only (no image payloads)
    for v in vectors.values():
        assert all(isinstance(x, float) for x in v.values)


# ===========================================================================
# Feature asset generation + integrity
# ===========================================================================
@pytest.mark.parametrize("name", VALID)
def test_feature_asset_generation(eeg_fixtures, tmp_path, name):
    tracker, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[name])
    out = feat_svc.generate_features(proc)
    assert out.accepted
    a = out.asset
    assert a.status == FeatureAssetStatus.GENERATED
    assert set(a.families) == {f.value for f in FeatureFamily}
    assert len(a.vectors) > 0
    assert feat_svc.integrity(a).ok, feat_svc.integrity(a).to_dict()
    assert tracker.verify_chain(a.lineage_id)
    assert {"patient", "case", "eeg", "processed_eeg", "feature"} <= {
        r.kind for r in tracker.chain(a.lineage_id)}


def test_integrity_has_eight_checks(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_EDF])
    asset = feat_svc.generate_features(proc).asset
    report = feat_svc.integrity(asset)
    assert report.ok
    assert report.to_dict()["n_checks"] == 8
    # the four content + four structural checks
    for expected in ("feature_completeness", "feature_integrity", "feature_consistency",
                     "feature_determinism", "registry_integrity", "audit_integrity",
                     "lineage_integrity", "version_integrity"):
        assert expected in {c["name"] for c in report.to_dict()["checks"]}


# ===========================================================================
# Registry
# ===========================================================================
def test_registry(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    a = feat_svc.generate_features(proc).asset
    assert feat_svc.registry.exists(a.feature_asset_id)
    assert a.feature_asset_id in feat_svc.registry.by_processed(proc.processed_id)
    assert a.feature_asset_id in feat_svc.registry.by_case(case.case_id)
    assert a.feature_asset_id in feat_svc.registry.by_patient(case.patient_id)
    assert a.feature_asset_id in feat_svc.registry.by_family("frequency")
    rec = feat_svc.registry.get(a.feature_asset_id)
    with pytest.raises(ValueError):
        feat_svc.registry.register(dataclasses.replace(rec, status=FeatureAssetStatus.QUARANTINED))


# ===========================================================================
# Audit
# ===========================================================================
def test_audit(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_EDF])
    a = feat_svc.generate_features(proc).asset
    log = feat_svc.audit_log_for(a.feature_asset_id)
    assert log.verify() and log.head == a.audit_head
    kinds = {e.kind for e in log.events()}
    assert {"features_extracted", "features_validated", "feature_lineage_recorded",
            "feature_version_changed", "feature_registered"} <= kinds
    fresh = make_feature_audit_log()
    fresh.append("features_extracted", {"a": 1})
    fresh.append("feature_registered", {"b": 2})
    assert fresh.verify()
    fresh._events[0] = dataclasses.replace(fresh._events[0], payload={"a": 999})
    assert fresh.verify() is False


# ===========================================================================
# Lineage
# ===========================================================================
def test_lineage_parents_processed(eeg_fixtures, tmp_path):
    tracker, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    a = feat_svc.generate_features(proc).asset
    node = tracker.get(a.lineage_id)
    assert proc.lineage_id in node.parents
    assert node.kind == "feature"


# ===========================================================================
# Validation
# ===========================================================================
def test_validation_content_checks(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_SET])
    a = feat_svc.generate_features(proc).asset
    assert a.validation.ok
    check_names = {n for n, _, _ in a.validation.checks}
    assert {"feature_completeness", "feature_integrity", "feature_consistency",
            "feature_determinism"} == check_names


def test_content_validator_detects_problems():
    v = FeatureContentValidator()
    bad = FeatureVector("x", FeatureFamily.FREQUENCY, FeatureGroup.BAND_POWER,
                        FeatureScope.PER_CHANNEL, ("c0", "c1"), (1.0,), (1,))  # n_values != n_ch
    name, ok, _ = v.feature_consistency([bad], n_channels=2)
    assert ok is False
    name, ok, detail = v.feature_completeness([], expected_families=["frequency"])
    assert ok is False and "frequency" in detail["missing_families"]


# ===========================================================================
# Reports
# ===========================================================================
def test_reports(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    a = feat_svc.generate_features(proc).asset
    r1 = feat_svc.reports(a)
    r2 = feat_svc.reports(a)
    assert set(r1) == {"frequency_report", "temporal_report", "connectivity_report",
                       "spectral_report", "topography_report", "registry_report",
                       "audit_report", "lineage_report", "validation_report"}
    assert r1 == r2
    assert r1["validation_report"]["ok"] is True
    assert r1["lineage_report"]["chain_verified"] is True
    assert r1["frequency_report"]["vectors"]


# ===========================================================================
# Schemas
# ===========================================================================
def test_schemas(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_SET])
    a = feat_svc.generate_features(proc).asset
    for name, payload in [
        ("FeatureRecord", a.to_dict()),
        ("FeatureMetadata", a.metadata.to_dict()),
        ("FeatureValidationRecord", a.validation.to_dict()),
        ("FeatureRegistryRecord", feat_svc.registry.get(a.feature_asset_id).to_dict()),
        ("FeatureVector", a.vectors[0].to_dict()),
    ]:
        ok, missing = validate_entity(name, payload)
        assert ok, (name, missing)
    for entity in ["FeatureIdentity", "FeatureRecord", "FeatureVector", "FeatureMetadata",
                   "FeatureValidationRecord", "FeatureRegistryRecord", "FeatureAuditRecord",
                   "FeatureLineageRecord"]:
        assert entity in ENTITY_CONTRACTS


# ===========================================================================
# Identity
# ===========================================================================
def test_identity_content_addressed():
    a = mint_identity("feature", {"processed_id": "signal+" + "a" * 16, "feature_key": "k1"})
    b = mint_identity("feature", {"processed_id": "signal+" + "a" * 16, "feature_key": "k1"})
    c = mint_identity("feature", {"processed_id": "signal+" + "a" * 16, "feature_key": "k2"})
    assert a.id == b.id and a.id != c.id
    assert a.id.startswith("feature+") and a.derived_from == "signal+" + "a" * 16
    with pytest.raises(IdentityError):
        mint_identity("feature", {"processed_id": "not-a-signal", "feature_key": "k"})
    assert validate_identity("feature+" + "a" * 16, "feature")[0] is True


# ===========================================================================
# Determinism
# ===========================================================================
def test_determinism(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    a = feat_svc.generate_features(proc).asset
    b = feat_svc.generate_features(proc).asset
    assert a.feature_asset_id == b.feature_asset_id
    assert a.version.version == b.version.version
    assert a.state_signature() == b.state_signature()
    # the determinism content check itself passed
    det = next(c for c in a.validation.checks if c[0] == "feature_determinism")
    assert det[1] is True


# ===========================================================================
# Edge cases
# ===========================================================================
def test_single_channel_and_flat_signal_edge_cases(eeg_fixtures, tmp_path):
    _, case, eeg_svc, sig_svc, feat_svc = _pipeline(tmp_path)
    proc = _processed(eeg_svc, sig_svc, case, eeg_fixtures[fx.VALID_FIF])
    data, sfreq, ch = _array(feat_svc, proc)
    # single channel (derived from the real asset) -> connectivity is 1x1, no errors
    single = data[:1]
    conn = {v.name: v for v in ConnectivityFeatureEngine().extract(single, sfreq, ch[:1])}
    assert conn["coherence_matrix"].shape == (1, 1)
    # flat signal -> all features finite
    flat = np.zeros_like(data)
    for eng in (FrequencyFeatureEngine(), TemporalFeatureEngine(), TopographyRepresentationEngine()):
        for v in eng.extract(flat, sfreq, ch):
            assert all(np.isfinite(x) for x in v.values)


# ===========================================================================
# Boundary
# ===========================================================================
def test_feature_engineering_respects_boundaries():
    root = REPO_ROOT / "backend" / "feature_engineering"
    forbidden = {"frontend", "tests", "scripts", "tools", "monitoring", "deployment"}
    uses_scipy = False
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
    assert uses_scipy, "feature engines must use real DSP (scipy)"
