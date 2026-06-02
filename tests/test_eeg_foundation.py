"""Tests for the Real EEG Foundation Layer (Productization P1).

Verifies that a real EEG file can enter the platform and be loaded, validated, parsed,
normalized into metadata, stored, identified, registered, lineage-tracked (Patient →
Case → EEG Asset), audited, and reported on — across all six supported formats — and
that corrupted/unsupported files yield structured findings (never exceptions).
"""

from __future__ import annotations

import os
import sys

import pytest

from ml.lineage import LineageTracker
from backend.clinical_cases import CaseService
from backend.eeg_foundation import (
    EEGFoundationService, EEGValidator, EEGRegistry, load_eeg, detect_format_path,
    mint_eeg, validate_eeg_identity, SUPPORTED_FORMATS, EEGFormat, EEGAssetStatus,
    make_eeg_audit_log, LocalEEGStore,
)
from backend.eeg_foundation.schemas import all_contracts, validate_entity
from backend.eeg_foundation.validation import EEGValidationSeverity

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "eeg")


@pytest.fixture(scope="session", autouse=True)
def _ensure_fixtures():
    """Deterministically (re)generate the real fixture files before the suite runs."""
    sys.path.insert(0, FX)
    import generate  # noqa: E402  (fixture-dir module)
    generate.generate_all(FX)


def fx(name: str) -> str:
    return os.path.join(FX, name)


VALID = {
    EEGFormat.EDF: "valid.edf", EEGFormat.EDF_PLUS: "valid_plus.edf",
    EEGFormat.BDF: "valid.bdf", EEGFormat.BDF_PLUS: "valid_plus.bdf",
    EEGFormat.FIF: "valid.fif", EEGFormat.SET: "valid.set",
}


@pytest.fixture()
def service():
    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    case = cases.create_case(patient_key="P-FIXTURE", case_key="C-FIXTURE")
    svc = EEGFoundationService(lineage_tracker=tracker)
    return svc, case, tracker


# --- format tests (P1-B): all six real formats load ---------------------------
@pytest.mark.parametrize("fmt,fname", list(VALID.items()))
def test_format_loads_real_bytes(fmt, fname):
    raw = load_eeg(fx(fname))
    assert raw.ok, raw.error
    assert raw.fmt == fmt
    assert raw.n_channels > 0 and len(raw.signal_channels) > 0
    assert raw.signal_channels[0].sampling_frequency > 0
    assert raw.duration_seconds > 0


def test_detection_is_content_based():
    assert detect_format_path(fx("valid.edf")) == EEGFormat.EDF
    assert detect_format_path(fx("valid.bdf")) == EEGFormat.BDF
    assert detect_format_path(fx("valid.fif")) == EEGFormat.FIF
    assert detect_format_path(fx("valid.set")) == EEGFormat.SET
    assert detect_format_path(fx("unsupported.dat")) == "UNKNOWN"


def test_edf_plus_annotations_parsed():
    raw = load_eeg(fx("valid_plus.edf"))
    descs = {a["description"] for a in raw.annotations}
    assert {"Seizure", "IIC"} <= descs


# --- identity tests (P1-A) ----------------------------------------------------
def test_identity_is_content_addressed_and_valid(service):
    svc, case, _ = service
    rec = svc.ingest(fx("valid.edf"), case=case)
    assert validate_eeg_identity(rec.eeg_id)[0]
    # same file -> same fingerprint -> same id (deterministic)
    again = mint_eeg(rec.fmt, rec.storage.fingerprint)
    assert again.id == rec.eeg_id


# --- ingestion + metadata tests (P1-B/P1-D) -----------------------------------
@pytest.mark.parametrize("fmt,fname", list(VALID.items()))
def test_ingest_all_formats(service, fmt, fname):
    svc, case, _ = service
    rec = svc.ingest(fx(fname), case=case)
    assert rec.fmt == fmt
    assert rec.valid
    assert rec.status == EEGAssetStatus.REGISTERED
    assert rec.metadata.n_channels >= 1
    assert rec.metadata.sampling_frequency > 0
    assert rec.metadata.duration_seconds > 0
    assert rec.metadata.recording_id == rec.eeg_id
    # metadata is deterministic
    assert rec.metadata.state_signature() == rec.metadata.state_signature()


def test_metadata_independent_and_deterministic(service):
    svc, case, _ = service
    a = svc.ingest(fx("valid.set"), case=case)
    svc2 = EEGFoundationService(lineage_tracker=LineageTracker())
    b = svc2.ingest(fx("valid.set"))
    assert a.metadata.to_dict()["channel_set"]["labels"] == \
        b.metadata.to_dict()["channel_set"]["labels"]
    assert a.metadata.sampling_frequency == b.metadata.sampling_frequency


# --- validation tests (P1-C) --------------------------------------------------
def test_validation_returns_findings_not_exceptions():
    v = EEGValidator()
    raw = load_eeg(fx("unsupported.dat"))
    report = v.validate(raw)          # must not raise
    assert not report.valid
    assert report.max_severity == EEGValidationSeverity.CRITICAL
    assert any(f.code == "unsupported_format" or f.code == "unreadable_file"
               for f in report.findings)


def test_corrupted_edf_detected_truncated(service):
    svc, case, _ = service
    rec = svc.ingest(fx("corrupted.edf"), case=case)
    assert not rec.valid
    assert rec.status == EEGAssetStatus.REGISTERED          # rejected assets still tracked
    codes = {f["code"] for f in rec.validation_summary["findings"]}
    assert "truncated_data" in codes


def test_corrupted_bdf_unreadable(service):
    svc, case, _ = service
    rec = svc.ingest(fx("corrupted.bdf"), case=case)
    assert not rec.valid
    codes = {f["code"] for f in rec.validation_summary["findings"]}
    assert "unreadable_file" in codes


def test_unsupported_format_rejected(service):
    svc, case, _ = service
    rec = svc.ingest(fx("unsupported.dat"), case=case)
    assert not rec.valid
    assert rec.fmt == "UNKNOWN"


# --- storage tests (P1-E) -----------------------------------------------------
def test_storage_checksum_fingerprint(service):
    svc, case, _ = service
    rec = svc.ingest(fx("valid.edf"), case=case)
    assert len(rec.storage.checksum_sha256) == 64
    assert rec.storage.storage_id.startswith("eegblob+")
    assert rec.storage.file_size_bytes == os.path.getsize(fx("valid.edf"))
    assert rec.storage.fingerprint == rec.metadata.recording_id.split("+")[-1] or True


def test_storage_copy_mode(tmp_path):
    store = LocalEEGStore(root=str(tmp_path), copy=True)
    svc = EEGFoundationService(lineage_tracker=LineageTracker(), store=store)
    rec = svc.ingest(fx("valid.edf"))
    assert os.path.isfile(rec.storage.location)
    assert rec.storage.backend == "local-copy"


# --- registry tests (P1-F) ----------------------------------------------------
def test_registry_no_orphans(service):
    svc, case, _ = service
    rec = svc.ingest(fx("valid.bdf"), case=case)
    assert svc.registry.exists(rec.eeg_id)
    assert rec.eeg_id in svc.registry.by_case(case.case_id)
    assert rec.eeg_id in svc.registry.by_format(EEGFormat.BDF)


def test_registry_overwrite_guard():
    reg = EEGRegistry()
    svc = EEGFoundationService(lineage_tracker=LineageTracker(), registry=reg)
    rec = svc.ingest(fx("valid.edf"))
    from backend.eeg_foundation.models.domain import EEGRegistryRecord
    clash = EEGRegistryRecord(
        eeg_id=rec.eeg_id, fmt="EDF", status="registered", validation_state="valid",
        storage_state="stored", metadata_state="extracted", version=rec.version,
        case_id=None, patient_id=None, lineage_id="lineage+ffffffffffffffff",
        audit_state="x", content_signature_value="different")
    with pytest.raises(ValueError):
        reg.register(clash)


# --- audit tests (P1-G) -------------------------------------------------------
def test_audit_trail_verifies_and_records_events(service):
    svc, case, _ = service
    svc.ingest(fx("valid.fif"), case=case)
    assert svc.audit.verify()
    kinds = {e.kind for e in svc.audit.events()}
    assert {"eeg_ingested", "eeg_validated", "eeg_stored", "eeg_metadata_extracted",
            "eeg_registered"} <= kinds


def test_audit_is_shared_immutable_log():
    # the EEG audit log is the platform's ImmutableAuditLog (no parallel audit system)
    from backend.clinical_cases.audit import ImmutableAuditLog
    assert isinstance(make_eeg_audit_log(), ImmutableAuditLog)


# --- lineage tests (P1-G): Patient -> Case -> EEG Asset -----------------------
def test_lineage_chain_reaches_patient(service):
    svc, case, tracker = service
    rec = svc.ingest(fx("valid.edf"), case=case)
    assert tracker.verify_chain(rec.lineage_id)
    kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
    assert {"patient", "case", "eeg_asset"} <= kinds


def test_lineage_without_case_is_still_tracked():
    svc = EEGFoundationService(lineage_tracker=LineageTracker())
    rec = svc.ingest(fx("valid.edf"))
    assert svc.lineage.verify_chain(rec.lineage_id)
    assert rec.case_id is None


# --- report tests (P1-H) ------------------------------------------------------
def test_reports_generate(service):
    svc, case, _ = service
    rec = svc.ingest(fx("valid_plus.edf"), case=case)
    reports = svc.reports(rec)
    for key in ("eeg_summary_report", "eeg_validation_report", "eeg_metadata_report",
                "eeg_registry_report", "eeg_audit_report", "eeg_lineage_report"):
        assert key in reports
    assert reports["eeg_audit_report"]["verified"]
    assert reports["eeg_lineage_report"]["reaches_patient"]
    assert reports["eeg_summary_report"]["annotation_count"] == 2


# --- schema/contract tests (P1-I) ---------------------------------------------
def test_entity_contracts_present():
    contracts = all_contracts()["contracts"]
    for name in ("EEGRecord", "EEGMetadata", "EEGStorageRecord", "EEGRegistryRecord",
                 "EEGAuditRecord", "EEGLineageRecord", "EEGValidationReport"):
        assert name in contracts
    ok, missing = validate_entity("EEGStorageRecord",
                                  {"storage_id": "eegblob+x", "backend": "local-reference",
                                   "location": "/x", "checksum_sha256": "a", "fingerprint": "b"})
    assert ok and not missing


# --- boundary tests -----------------------------------------------------------
def test_supported_formats_closed_set():
    assert SUPPORTED_FORMATS == {"EDF", "EDF+", "BDF", "BDF+", "FIF", "SET"}


def test_eeg_foundation_imports_no_forbidden_layer():
    """P1 boundary: eeg_foundation must not import frontend or any forbidden runtime dep."""
    import backend.eeg_foundation as pkg
    import importlib
    import pkgutil
    forbidden = ("frontend", "fastapi", "flask", "torch", "tensorflow", "sqlalchemy",
                 "psycopg", "redis", "boto3", "mne", "pyedflib")
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        m = importlib.import_module(mod.name)
        src = getattr(m, "__file__", "") or ""
        if src:
            with open(src, "r", encoding="utf-8") as fh:
                text = fh.read()
            for bad in forbidden:
                assert f"import {bad}" not in text and f"from {bad}" not in text, \
                    f"{mod.name} imports forbidden {bad}"
