"""Tests for the Real EEG Foundation Layer (Productization P1).

Covers every mandated category: identity, ingestion, format detection, metadata,
validation, registry, audit, lineage, storage, reports, boundaries, corrupted
files, and unsupported formats — over small, real, deterministic EEG fixtures
(EDF/EDF+/BDF/BDF+/FIF/SET) that MNE-Python actually decodes.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import (
    EEGFoundationService, LocalEEGStore, EEGFileValidator, EEGFormat, EEGAssetStatus,
    EEGValidationSeverity, load_eeg, detect_format, detect_format_from_bytes,
    extract_metadata, mint_identity, validate_identity, IdentityError,
    make_eeg_audit_log, fingerprint_of_checksum,
)
from backend.eeg_foundation.schemas import ENTITY_CONTRACTS, validate_entity
from ml.provenance import sha256_of_file

import _eeg_fixtures as fx

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

VALID = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
EXPECTED_FORMAT = {
    fx.VALID_EDF: EEGFormat.EDF, fx.VALID_EDF_PLUS: EEGFormat.EDF_PLUS,
    fx.VALID_BDF: EEGFormat.BDF, fx.VALID_BDF_PLUS: EEGFormat.BDF_PLUS,
    fx.VALID_FIF: EEGFormat.FIF, fx.VALID_SET: EEGFormat.SET,
}
ANNOTATED = {fx.VALID_EDF_PLUS, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET}


def _env(tmp_path):
    """Create a shared lineage tracker, a Case, and an EEG service over it."""
    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    case = cases.create_case(patient_key="P-001", case_key="C-001")
    store = LocalEEGStore(str(tmp_path / "eeg_store"))
    svc = EEGFoundationService(store, lineage_tracker=tracker)
    return tracker, case, svc


def _ingest(svc, case, path):
    return svc.ingest_eeg(path, case_id=case.case_id, patient_id=case.patient_id,
                          case_lineage_id=case.lineage_id)


# =============================================================================
# Format detection
# =============================================================================
@pytest.mark.parametrize("name", VALID)
def test_format_detection_valid(eeg_fixtures, name):
    detected, declared = detect_format(eeg_fixtures[name])
    assert detected == EXPECTED_FORMAT[name]


def test_format_detection_distinguishes_plus_variants(eeg_fixtures):
    assert detect_format(eeg_fixtures[fx.VALID_EDF])[0] == EEGFormat.EDF
    assert detect_format(eeg_fixtures[fx.VALID_EDF_PLUS])[0] == EEGFormat.EDF_PLUS
    assert detect_format(eeg_fixtures[fx.VALID_BDF])[0] == EEGFormat.BDF
    assert detect_format(eeg_fixtures[fx.VALID_BDF_PLUS])[0] == EEGFormat.BDF_PLUS


def test_format_detection_unsupported(eeg_fixtures):
    detected, _ = detect_format(eeg_fixtures[fx.UNSUPPORTED])
    assert detected is None
    assert detect_format_from_bytes(b"") is None
    assert detect_format_from_bytes(b"random noise not an eeg header") is None


def test_supported_format_vocabulary_is_closed():
    assert {f.value for f in EEGFormat} == {"EDF", "EDF+", "BDF", "BDF+", "FIF", "SET"}


# =============================================================================
# Ingestion (real files)
# =============================================================================
@pytest.mark.parametrize("name", VALID)
def test_ingestion_reads_real_files(eeg_fixtures, name):
    parsed = load_eeg(eeg_fixtures[name])
    assert parsed.parse_ok, parsed.error
    assert parsed.detected_format == EXPECTED_FORMAT[name]
    assert parsed.n_channels == 3
    assert parsed.sampling_frequency == 256.0
    assert parsed.duration_seconds == pytest.approx(2.0)
    assert parsed.n_samples == 512
    assert [c.label for c in parsed.channels] == ["Fp1", "Fp2", "Cz"]
    assert parsed.file_size_bytes > 0
    assert len(parsed.checksum_sha256) == 64


@pytest.mark.parametrize("name", VALID)
def test_ingestion_extracts_annotations(eeg_fixtures, name):
    parsed = load_eeg(eeg_fixtures[name])
    descriptions = {desc for _, _, desc in parsed.annotations}
    if name in ANNOTATED:
        assert "seizure_onset" in descriptions
        assert len(parsed.annotations) == 2
    else:
        assert len(parsed.annotations) == 0


def test_ingestion_never_raises_on_garbage(tmp_path):
    bad = tmp_path / "x.edf"
    bad.write_bytes(b"\x00\x01\x02 not an edf")
    parsed = load_eeg(str(bad))
    assert parsed.parse_ok is False  # no exception escaped


# =============================================================================
# Identity
# =============================================================================
def test_identity_is_deterministic_and_content_addressed():
    a = mint_identity("eeg", {"case_id": "case+" + "a" * 16, "eeg_key": "deadbeefdeadbeef"})
    b = mint_identity("eeg", {"case_id": "case+" + "a" * 16, "eeg_key": "deadbeefdeadbeef"})
    assert a.id == b.id
    assert a.id.startswith("eeg+") and len(a.id.split("+")[1]) == 16
    assert a.derived_from == "case+" + "a" * 16
    # different file fingerprint -> different asset id
    c = mint_identity("eeg", {"case_id": "case+" + "a" * 16, "eeg_key": "0000000000000000"})
    assert c.id != a.id


def test_identity_rejects_bad_parent_and_unmintable_kinds():
    with pytest.raises(IdentityError):
        mint_identity("eeg", {"case_id": "not-a-case", "eeg_key": "x"})
    with pytest.raises(IdentityError):
        mint_identity("case", {"patient_id": "patient+" + "a" * 16, "case_key": "k"})  # referenced-only
    assert validate_identity("eeg+" + "a" * 16, "eeg")[0] is True
    assert validate_identity("eeg+nothex", "eeg")[0] is False


# =============================================================================
# Metadata
# =============================================================================
@pytest.mark.parametrize("name", VALID)
def test_metadata_extraction_deterministic(eeg_fixtures, name):
    parsed = load_eeg(eeg_fixtures[name])
    m1 = extract_metadata(parsed)
    m2 = extract_metadata(load_eeg(eeg_fixtures[name]))
    assert m1.to_dict() == m2.to_dict()
    assert m1.signature() == m2.signature()
    assert m1.recording_id.startswith("recording+")
    assert m1.n_channels == 3
    assert m1.channel_labels == ("Fp1", "Fp2", "Cz")
    assert m1.eeg_format == EXPECTED_FORMAT[name]
    assert m1.sampling_frequency == 256.0
    assert m1.duration_seconds == pytest.approx(2.0)
    if name in ANNOTATED:
        assert m1.n_annotations == 2
        assert "seizure_onset" in m1.annotation_types


def test_metadata_stored_independently_of_raw_bytes(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF])
    md = out.asset.metadata.to_dict()
    # metadata is a plain JSON-able dict carrying no raw signal arrays
    assert "data" not in md and "signal" not in md
    assert md["n_channels"] == 3 and md["sampling_frequency"] == 256.0


# =============================================================================
# Validation (structured findings, never exceptions)
# =============================================================================
@pytest.mark.parametrize("name", VALID)
def test_validation_accepts_valid_files(eeg_fixtures, name):
    parsed, result = EEGFileValidator().validate_path(eeg_fixtures[name])
    assert result.ok is True
    assert result.has_errors is False
    # legitimate .edf/.bdf extension for a + variant must NOT warn (family-aware)
    assert not any(f.code == "format_mismatch" for f in result.findings)


def test_validation_corrupted_file_is_a_finding_not_an_exception(eeg_fixtures):
    for name in (fx.CORRUPTED_EDF, fx.CORRUPTED_BDF):
        parsed, result = EEGFileValidator().validate_path(eeg_fixtures[name])
        assert parsed.parse_ok is False
        assert parsed.detected_format is not None  # recognized, but undecodable
        assert result.has_errors is True
        codes = {f.code for f in result.findings}
        assert "corrupted_file" in codes
        assert any(f.severity == EEGValidationSeverity.CRITICAL for f in result.findings)


def test_validation_unsupported_format(eeg_fixtures):
    parsed, result = EEGFileValidator().validate_path(eeg_fixtures[fx.UNSUPPORTED])
    assert parsed.detected_format is None
    assert {f.code for f in result.findings} == {"unsupported_format"}
    assert result.has_errors is True


def test_validation_unreadable_file(tmp_path):
    parsed, result = EEGFileValidator().validate_path(str(tmp_path / "does_not_exist.edf"))
    assert parsed.parse_ok is False
    assert any(f.code == "unreadable_file" for f in result.findings)


# =============================================================================
# Storage
# =============================================================================
def test_storage_roundtrip_and_integrity(eeg_fixtures, tmp_path):
    store = LocalEEGStore(str(tmp_path / "store"))
    rec = store.put(eeg_fixtures[fx.VALID_EDF], eeg_format=EEGFormat.EDF)
    assert store.exists(rec) and store.verify(rec) is True
    assert rec.checksum_sha256 == sha256_of_file(eeg_fixtures[fx.VALID_EDF])
    assert rec.content_fingerprint == fingerprint_of_checksum(rec.checksum_sha256)
    assert rec.file_size_bytes > 0
    # tamper detection
    with open(store.abs_path(rec), "ab") as fh:
        fh.write(b"tampered")
    assert store.verify(rec) is False


def test_storage_is_content_addressed_idempotent(eeg_fixtures, tmp_path):
    store = LocalEEGStore(str(tmp_path / "store"))
    a = store.put(eeg_fixtures[fx.VALID_BDF], eeg_format=EEGFormat.BDF)
    b = store.put(eeg_fixtures[fx.VALID_BDF], eeg_format=EEGFormat.BDF)
    assert a.storage_id == b.storage_id
    assert a.raw_file_reference == b.raw_file_reference


# =============================================================================
# Registry (no orphans, no silent overwrite)
# =============================================================================
def test_registry_tracks_asset(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_FIF])
    asset = out.asset
    assert svc.registry.exists(asset.asset_id)
    rec = svc.registry.get(asset.asset_id)
    assert rec.eeg_format == EEGFormat.FIF
    assert rec.status == EEGAssetStatus.REGISTERED
    assert rec.lineage_id == asset.lineage_id
    assert asset.asset_id in svc.registry.by_case(case.case_id)
    assert asset.asset_id in svc.registry.by_patient(case.patient_id)


def test_registry_rejects_silent_overwrite(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF])
    rec = svc.registry.get(out.asset.asset_id)
    tampered = dataclasses.replace(rec, status=EEGAssetStatus.QUARANTINED)
    with pytest.raises(ValueError):
        svc.registry.register(tampered)  # same (id, version), different content


# =============================================================================
# Audit (immutable, tamper-evident)
# =============================================================================
def test_audit_trail_generated(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF])
    log = svc.audit_log_for(out.asset.asset_id)
    assert log.verify() is True
    assert log.head == out.asset.audit_head
    kinds = [e.kind for e in log.events()]
    for expected in ["eeg_ingested", "eeg_validated", "eeg_metadata_extracted",
                     "eeg_stored", "eeg_lineage_recorded", "eeg_version_changed",
                     "eeg_registered"]:
        assert expected in kinds


def test_audit_chain_is_tamper_evident():
    log = make_eeg_audit_log()
    log.append("eeg_ingested", {"a": 1})
    log.append("eeg_stored", {"b": 2})
    assert log.verify() is True
    log._events[0] = dataclasses.replace(log._events[0], payload={"a": 999})
    assert log.verify() is False


# =============================================================================
# Lineage (Patient -> Case -> EEG)
# =============================================================================
@pytest.mark.parametrize("name", VALID)
def test_lineage_chain_reaches_patient(eeg_fixtures, tmp_path, name):
    tracker, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[name])
    asset = out.asset
    assert tracker.verify_chain(asset.lineage_id) is True
    kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
    assert {"patient", "case", "eeg"} <= kinds
    eeg_node = tracker.get(asset.lineage_id)
    assert case.lineage_id in eeg_node.parents


# =============================================================================
# Reports (deterministic)
# =============================================================================
def test_reports_generated_and_deterministic(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF_PLUS])
    r1 = svc.reports(out.asset)
    r2 = svc.reports(out.asset)
    assert set(r1) == {
        "eeg_summary_report", "eeg_metadata_report", "eeg_validation_report",
        "eeg_audit_report", "eeg_lineage_report", "eeg_registry_report",
    }
    assert r1 == r2  # deterministic
    assert r1["eeg_audit_report"]["chain_verified"] is True
    assert r1["eeg_lineage_report"]["chain_verified"] is True
    assert r1["eeg_registry_report"]["n_assets"] == 1


# =============================================================================
# Service behaviour: REGISTERED / QUARANTINED / rejected
# =============================================================================
def test_corrupted_file_is_quarantined_but_tracked(eeg_fixtures, tmp_path):
    tracker, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.CORRUPTED_EDF])
    assert out.accepted is True
    assert out.asset.status == EEGAssetStatus.QUARANTINED
    assert out.validation.has_errors is True
    assert svc.registry.exists(out.asset.asset_id)
    assert tracker.verify_chain(out.asset.lineage_id) is True
    assert svc.integrity(out.asset).ok is True


def test_unsupported_file_is_rejected(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.UNSUPPORTED])
    assert out.accepted is False
    assert out.asset is None
    assert out.reason == "unsupported_format"
    assert out.validation.has_errors is True


def test_ingestion_is_idempotent(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    a = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF]).asset
    b = _ingest(svc, case, eeg_fixtures[fx.VALID_EDF]).asset
    assert a.asset_id == b.asset_id  # content-addressed
    assert a.version.version == b.version.version
    assert svc.registry.list_assets() == [a.asset_id]


@pytest.mark.parametrize("name", VALID)
def test_integrity_validator_passes_for_registered_assets(eeg_fixtures, tmp_path, name):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[name])
    report = svc.integrity(out.asset)
    assert report.ok, report.to_dict()
    assert report.to_dict()["n_checks"] == 8


# =============================================================================
# Schemas / contracts (no undocumented objects)
# =============================================================================
def test_entity_contracts_validate_built_asset(eeg_fixtures, tmp_path):
    _, case, svc = _env(tmp_path)
    out = _ingest(svc, case, eeg_fixtures[fx.VALID_SET])
    asset = out.asset
    for name, payload in [
        ("EEGRecord", asset.to_dict()),
        ("EEGMetadata", asset.metadata.to_dict()),
        ("EEGStorageRecord", asset.storage.to_dict()),
        ("EEGRegistryRecord", svc.registry.get(asset.asset_id).to_dict()),
        ("EEGValidationResult", asset.validation.to_dict()),
    ]:
        ok, missing = validate_entity(name, payload)
        assert ok, (name, missing)
    # every directive-named entity has a documented contract
    for entity in ["EEGIdentity", "EEGRecord", "EEGMetadata", "EEGSource", "EEGFormat",
                   "EEGChannel", "EEGChannelSet", "EEGAnnotation", "EEGStorageRecord",
                   "EEGAuditRecord", "EEGLineageRecord", "EEGRegistryRecord"]:
        assert entity in ENTITY_CONTRACTS


# =============================================================================
# Boundary (the EEG layer never imports frontend; uses the real reader)
# =============================================================================
def test_eeg_foundation_respects_boundaries():
    root = REPO_ROOT / "backend" / "eeg_foundation"
    forbidden = {"frontend", "tests", "scripts", "tools", "monitoring", "deployment", "evaluation"}
    uses_mne = False
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            roots = []
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                roots = [node.module.split(".")[0]]
            assert not (set(roots) & forbidden), f"{path} imports forbidden module"
            if "mne" in roots:
                uses_mne = True
    assert uses_mne, "ingestion must use the real MNE reader (no fake parser)"
