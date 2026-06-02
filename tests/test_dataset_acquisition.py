"""Track 1 — Real Dataset Platform tests (backend/dataset_acquisition).

Exercises acquisition tracking, discovery, structure validation, metadata + label
extraction, recording inventory, readiness scoring, audit + lineage integration, registry,
reports, determinism, and the boundary / corrupted / missing-label / missing-metadata
conditions — driving the **real** ``eeg_foundation`` MNE reader over the committed real EDF
fixtures laid out as a CHB-MIT dataset (no network). A real-corpus test additionally runs
over the locally-acquired PhysioNet recordings **when available**.
"""

from __future__ import annotations

import pytest

from _track1_helpers import build_local_chb_mit, real_chb_mit_root

from backend.dataset_acquisition import (
    AccessRequirement, AvailabilityState, DatasetSource, DatasetStorageManager,
    DatasetVerificationManager, EntityKind, LabelScheme, LabelValue, RealDatasetService,
    TrainingReadinessClass, all_specs, connector_for, parse_chb_summary, spec_for, validate_entity,
)


# --- T1-A acquisition --------------------------------------------------------
def test_acquisition_specs_cover_all_mandatory_sources():
    specs = {s.source for s in all_specs()}
    assert specs == {DatasetSource.CHB_MIT, DatasetSource.TUH_EEG, DatasetSource.TEMPLE_EEG,
                     DatasetSource.SIENA_SCALP, DatasetSource.BONN}
    chb = spec_for(DatasetSource.CHB_MIT)
    assert chb.access_requirement == AccessRequirement.OPEN and chb.auto_downloadable
    # Approval-gated corpora are documented but never auto-downloadable.
    for src in (DatasetSource.TUH_EEG, DatasetSource.TEMPLE_EEG):
        assert spec_for(src).access_requirement == AccessRequirement.REGISTRATION_REQUIRED
        assert not spec_for(src).auto_downloadable


def test_acquisition_does_not_auto_download_registration_sources(tmp_path):
    svc = RealDatasetService(data_root=str(tmp_path))
    # allow_download=True, but TUH requires a signed agreement -> never attempted, no network.
    rec = svc.acquire(DatasetSource.TUH_EEG, allow_download=True)
    assert rec.attempted is False
    assert all(i.state == AvailabilityState.UNAVAILABLE for i in rec.items)
    assert "agreement" in rec.note or "registration" in rec.note


def test_acquisition_plan_is_offline_and_complete(tmp_path):
    svc = RealDatasetService(data_root=str(tmp_path))
    plan = svc.acquisition_plan()
    assert {r.source for r in plan} == {s.source for s in all_specs()}
    # No data present in the fresh temp root -> nothing acquired.
    assert all(r.n_acquired == 0 for r in plan)


# --- T1-B local management ---------------------------------------------------
def test_availability_tracking_verified(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
    assert out.availability.state == AvailabilityState.VERIFIED
    assert out.availability.n_files == 3 and out.availability.n_verified == 3
    assert out.availability.missing_files == () and out.availability.corrupted_files == ()


def test_verification_detects_corruption(tmp_path):
    storage = DatasetStorageManager(str(tmp_path))
    storage.ensure_root(DatasetSource.CHB_MIT)
    empty = storage.abspath(DatasetSource.CHB_MIT, "empty.edf")
    open(empty, "wb").close()
    verifier = DatasetVerificationManager(storage)
    rec = verifier.verify_file(DatasetSource.CHB_MIT, "empty.edf")
    assert rec.state == AvailabilityState.CORRUPTED
    # checksum mismatch is also corruption
    good = storage.abspath(DatasetSource.CHB_MIT, "x.edf")
    open(good, "wb").write(b"abc")
    rec2 = verifier.verify_file(DatasetSource.CHB_MIT, "x.edf", expected_checksum="deadbeef")
    assert rec2.state == AvailabilityState.CORRUPTED
    missing = verifier.verify_file(DatasetSource.CHB_MIT, "nope.edf")
    assert missing.state == AvailabilityState.UNAVAILABLE


# --- T1-C connectors (ACTUAL files) ------------------------------------------
def test_discovery_and_metadata_from_actual_files(tmp_path):
    build_local_chb_mit(str(tmp_path))
    storage = DatasetStorageManager(str(tmp_path))
    result = connector_for(DatasetSource.CHB_MIT, storage).connect()
    assert len(result.discovered_files) == 2
    assert len(result.recordings) == 2
    for r in result.recordings:
        assert r.parse_ok and r.sampling_frequency == 256.0 and r.n_channels == 3
        assert r.n_samples == 512 and abs(r.duration_seconds - 2.0) < 1e-6
        assert r.patient_id == "chb01"
    assert {p.patient_key for p in result.patients} == {"chb01"}


def test_label_extraction_from_real_summary(tmp_path):
    build_local_chb_mit(str(tmp_path))
    storage = DatasetStorageManager(str(tmp_path))
    result = connector_for(DatasetSource.CHB_MIT, storage).connect()
    by_value = {label.value for label in result.labels}
    assert by_value == {LabelValue.SEIZURE, LabelValue.BACKGROUND}
    seizure = next(label for label in result.labels if label.value == LabelValue.SEIZURE)
    assert seizure.scheme == LabelScheme.CHB_MIT_SEIZURE and seizure.n_events == 1
    assert seizure.events[0].start_seconds == 1.0 and seizure.events[0].end_seconds == 2.0


def test_parse_chb_summary_both_formats():
    early = parse_chb_summary(
        "File Name: chb01_03.edf\nNumber of Seizures in File: 1\n"
        "Seizure Start Time: 2996 seconds\nSeizure End Time: 3036 seconds\n")
    assert early["chb01_03.edf"] == (1, [(2996.0, 3036.0)])
    indexed = parse_chb_summary(
        "File Name: chb24_01.edf\nNumber of Seizures in File: 2\n"
        "Seizure 1 Start Time: 480 seconds\nSeizure 1 End Time: 505 seconds\n"
        "Seizure 2 Start Time: 2451 seconds\nSeizure 2 End Time: 2476 seconds\n")
    assert indexed["chb24_01.edf"] == (2, [(480.0, 505.0), (2451.0, 2476.0)])


# --- T1-D / E / F / G --------------------------------------------------------
def test_structure_validation_passes(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    assert out.validation.ok and out.validation.n_checks == 9
    assert out.validation.n_blocking_failed == 0


def test_label_verification_complete_and_multiclass(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    lv = out.label_verification
    assert lv.coverage == 1.0 and lv.consistent and lv.n_classes == 2
    assert lv.n_missing == 0 and lv.n_corrupted == 0 and lv.n_unsupported == 0


def test_recording_inventory_actual_counts(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    inv = out.inventory
    assert inv.n_recordings == 2 and inv.n_patients == 1 and inv.n_labels == 2
    assert inv.sampling_frequencies == (256.0,)
    assert inv.n_channels_distribution == {"3": 2}


def test_readiness_ready_for_training(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    assert out.readiness.classification == TrainingReadinessClass.READY_FOR_TRAINING
    assert out.readiness.score >= 0.9
    assert all(v == 1.0 for v in out.readiness.dimensions.values())
    assert out.ready_for_training


# --- T1-H audit + lineage ----------------------------------------------------
def test_audit_integration(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    out = svc.integrate(DatasetSource.CHB_MIT)
    log = svc.audit_log_for(out.dataset_id)
    assert log.verify() and len(log) == 9 and out.dataset_record.audit_head == log.head


def test_lineage_chain_reaches_source(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    out = svc.integrate(DatasetSource.CHB_MIT)
    assert svc.lineage.verify_chain(out.registry_lineage_id)
    kinds = {n.kind for n in svc.lineage.chain(out.registry_lineage_id)}
    assert {"dataset_source", "real_dataset", "dataset_patient", "dataset_recording",
            "dataset_label", "dataset_registry"} <= kinds


def test_registry_has_no_orphans(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    svc.integrate(DatasetSource.CHB_MIT)
    counts = svc.registry.counts()
    assert svc.registry.orphans() == []
    assert counts[EntityKind.DATASET.value] == 1 and counts[EntityKind.RECORDING.value] == 2
    assert counts[EntityKind.LABEL.value] == 2 and counts[EntityKind.PATIENT.value] == 1


# --- T1-I reports ------------------------------------------------------------
def test_reports_generate(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    out = svc.integrate(DatasetSource.CHB_MIT)
    reports = svc.reports(out)
    expected = {"acquisition_report", "validation_report", "inventory_report", "label_report",
                "metadata_report", "readiness_report", "audit_report", "lineage_report",
                "dataset_summary_report"}
    assert set(reports) == expected


def test_entity_contract_validation(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    ok, missing = validate_entity("RealDatasetRecord", out.dataset_record.to_dict())
    assert ok and missing == []


# --- determinism -------------------------------------------------------------
def test_determinism_across_instances(tmp_path):
    build_local_chb_mit(str(tmp_path))
    a = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    b = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    assert a.dataset_id == b.dataset_id
    assert a.dataset_record.content_fingerprint == b.dataset_record.content_fingerprint
    assert a.readiness.score == b.readiness.score
    assert a.readiness.readiness_id == b.readiness.readiness_id


# --- failure / edge conditions ----------------------------------------------
def test_missing_labels_blocks_training_readiness(tmp_path):
    build_local_chb_mit(str(tmp_path), with_summary=False)
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    assert out.label_verification.coverage == 0.0
    assert out.label_verification.n_missing == 2
    assert out.readiness.classification != TrainingReadinessClass.READY_FOR_TRAINING


def test_corrupted_recording_blocks_readiness(tmp_path):
    build_local_chb_mit(str(tmp_path), corrupt_one=True)
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    # the corrupted recording fails to parse -> structure validation has a blocking failure
    assert not out.validation.ok
    assert out.readiness.classification != TrainingReadinessClass.READY_FOR_TRAINING


def test_unavailable_dataset_is_not_ready_without_crashing(tmp_path):
    # No files at all -> graceful NOT_READY (never raises).
    out = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    assert out.accepted
    assert out.dataset_record.n_recordings == 0
    assert out.readiness.classification == TrainingReadinessClass.NOT_READY


# --- real corpus when available ---------------------------------------------
def test_real_chb_mit_corpus_when_available():
    root = real_chb_mit_root()
    if root is None:
        pytest.skip("real CHB-MIT corpus not acquired locally (run scripts.acquire_real_dataset)")
    svc = RealDatasetService(data_root=root)
    out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
    assert out.ready_for_training
    # genuine PhysioNet recordings: 256 Hz, 23 bipolar channels, 1-hour files
    assert out.inventory.sampling_frequencies == (256.0,)
    assert out.inventory.n_channels_distribution == {"23": 2}
    # the real documented chb01_03 seizure interval
    seizure = next(label for label in out.connector_result.labels
                   if label.value == LabelValue.SEIZURE)
    assert seizure.events[0].start_seconds == 2996.0 and seizure.events[0].end_seconds == 3036.0
