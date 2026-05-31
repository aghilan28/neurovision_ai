"""Tests for DRP-4 — Persistence Platform (``backend/persistence_platform``).

Exercises the storage engine, repositories, registry/audit/lineage persistence, the recovery
engine, validation, readiness, reports, schemas, and boundary/corrupted/missing/partial
conditions — using the **real** DRP-1 datasets / DRP-2 models / DRP-3 serving records (no
replacement systems).
"""

from __future__ import annotations

import dataclasses

import pytest

from ml.lineage import LineageTracker
from backend.persistence_platform import (
    PersistencePlatformService, PersistenceStatus, RecoveryStatus, ReadinessClass,
    StorageEngine, StorageError, Repository, RepositoryKind, PersistenceReadinessEngine,
    AuditStore, AuditPersistenceError, ENTITY_CONTRACTS, validate_entity, make_persistence_audit_log,
)

from _drp4_helpers import build_platform_state


def _persisted(eeg_fixtures, tmp_path):
    tracker, ctx, state = build_platform_state(eeg_fixtures, tmp_path / "build")
    svc = PersistencePlatformService(storage_root=str(tmp_path / "store"), lineage_tracker=tracker)
    return tracker, ctx, state, svc, svc.persist(state)


# =============================================================================
# Storage engine (DRP4-C)
# =============================================================================
def test_storage_engine_durable_and_tamper_evident(tmp_path):
    eng = StorageEngine(str(tmp_path / "s"))
    sr = eng.put("registry", "demo", {"b": 2, "a": 1})
    assert eng.exists("registry", "demo") and eng.verify(sr)
    assert eng.get("registry", "demo", expected_checksum=sr.checksum) == {"a": 1, "b": 2}
    # a fresh engine at the same root still reads it (durable / restart-recoverable)
    eng2 = StorageEngine(str(tmp_path / "s"))
    assert eng2.get("registry", "demo") == {"a": 1, "b": 2}
    # tamper detection
    with open(eng._path("registry", "demo"), "w") as fh:
        fh.write('{"a":1,"b":3}')
    assert not eng2.verify(sr)
    with pytest.raises(StorageError):
        eng2.get("registry", "demo", expected_checksum=sr.checksum)


def test_storage_get_missing_raises(tmp_path):
    eng = StorageEngine(str(tmp_path / "s"))
    with pytest.raises(StorageError):
        eng.get("registry", "nope")


# =============================================================================
# Repositories (DRP4-D)
# =============================================================================
def test_repository_saves_and_reloads(tmp_path):
    eng = StorageEngine(str(tmp_path / "s"))
    repo = Repository(eng, RepositoryKind.MODEL)
    manifest = repo.save_all({"model+" + "a" * 16: {"x": 1}, "model+" + "b" * 16: {"y": 2}})
    assert manifest.n_records == 2 and manifest.repository_kind == "model"
    assert repo.load("model+" + "a" * 16) == {"x": 1}
    # reload from a fresh repository over the same root
    repo2 = Repository(StorageEngine(str(tmp_path / "s")), RepositoryKind.MODEL)
    assert set(repo2.list_ids()) == {"model+" + "a" * 16, "model+" + "b" * 16}


# =============================================================================
# Persist + recover end to end (DRP4-E/F/G/H/I)
# =============================================================================
def test_persist_then_cold_restart_recovery(eeg_fixtures, tmp_path):
    tracker, ctx, state, svc, out = _persisted(eeg_fixtures, tmp_path)
    assert out.accepted and out.reason == PersistenceStatus.PERSISTED.value
    record = out.record
    # registries + audit + lineage + execution all persisted
    assert {r.registry_name for r in record.registry_storage} == {
        "model_registry", "dataset_registry", "serving_registry"}
    assert record.lineage_storage.n_nodes > 0 and record.audit_storage
    assert {e.history_kind for e in record.execution_storage} == {"serving", "inference"}
    # the in-process recovery verified durability
    assert out.recovery.status == RecoveryStatus.RECOVERED and out.recovery.anchor_verified
    assert out.readiness.classification == ReadinessClass.READY
    assert svc.integrity(record).ok, [c.name for c in svc.integrity(record).failures()]

    # COLD RESTART: a brand-new service + fresh lineage tracker at the same storage root
    svc2 = PersistencePlatformService(storage_root=svc.storage_root, lineage_tracker=LineageTracker())
    rec = svc2.recover(record.persistence_id)
    assert rec.status == RecoveryStatus.RECOVERED and rec.anchor_verified
    # registries recovered with their content
    assert ctx["model"].model_id in rec.registries["model_registry"]["models"]
    # audit logs recovered + re-verify (immutable history survived)
    assert all(lg.verify() for lg in rec.audit_logs.values())
    # lineage rebuilt + the recovery-event chain reaches the patient
    assert rec.lineage_tracker.verify_chain(rec.lineage_id)
    kinds = {n.kind for n in rec.lineage_tracker.chain(rec.lineage_id)}
    assert {"patient", "model", "serving_response", "persistence_record",
            "recovery_event"} <= kinds


def test_persistence_record_is_immutable(eeg_fixtures, tmp_path):
    _, _, _, _, out = _persisted(eeg_fixtures, tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        out.record.status = PersistenceStatus.FAILED


def test_traceability_chain(eeg_fixtures, tmp_path):
    tracker, _, _, _, out = _persisted(eeg_fixtures, tmp_path)
    assert tracker.verify_chain(out.record.lineage_id)
    kinds = {n.kind for n in tracker.chain(out.record.lineage_id)}
    assert {"patient", "case", "feature", "dataset", "model", "prediction", "serving_execution",
            "serving_response", "persistence_record"} <= kinds


# =============================================================================
# Audit persistence reproduces the chain head (DRP4-F)
# =============================================================================
def test_audit_recovery_reproduces_head(tmp_path):
    eng = StorageEngine(str(tmp_path / "s"))
    log = make_persistence_audit_log()
    log.append("a", {"x": 1})
    log.append("b", {"y": 2})
    store = AuditStore(eng)
    sr, asr = store.persist("demo", log)
    recovered = store.recover(sr)
    assert recovered.head == log.head and recovered.verify() and len(recovered) == 2
    # corrupt the persisted head -> recovery refuses (no silent acceptance)
    bad = eng.get("audit", "demo")
    bad["head"] = "deadbeefdeadbeef"
    eng.put("audit", "demo", bad)
    sr2 = dataclasses.replace(sr, checksum=eng.put("audit", "demo", bad).checksum)
    with pytest.raises(AuditPersistenceError):
        store.recover(sr2)


# =============================================================================
# Readiness engine (DRP4-K)
# =============================================================================
def test_readiness_requires_all_evidence():
    eng = PersistenceReadinessEngine()
    tid = "persistence_record+" + "a" * 16
    ready = eng.assess(target_id=tid, storage_ok=True, registry_ok=True, recovery_ok=True,
                       audit_ok=True, lineage_ok=True, validation_ok=True)
    assert ready.classification == ReadinessClass.READY and ready.score == pytest.approx(1.0)
    no_recovery = eng.assess(target_id=tid, storage_ok=True, registry_ok=True, recovery_ok=False,
                             audit_ok=True, lineage_ok=True, validation_ok=True)
    assert no_recovery.classification != ReadinessClass.READY
    assert "recovery_readiness" in no_recovery.findings
    bad = eng.assess(target_id=tid, storage_ok=False, registry_ok=False, recovery_ok=False,
                     audit_ok=False, lineage_ok=False, validation_ok=False)
    assert bad.classification == ReadinessClass.NOT_READY


# =============================================================================
# Reports (DRP4-M) + schemas (DRP4-N)
# =============================================================================
def test_reports_generate(eeg_fixtures, tmp_path):
    _, _, _, svc, out = _persisted(eeg_fixtures, tmp_path)
    reports = svc.reports(out.record)
    expected = {"storage_report", "registry_report", "audit_persistence_report",
                "lineage_persistence_report", "recovery_report", "validation_report",
                "readiness_report", "persistence_summary_report"}
    assert expected == set(reports)
    assert reports["persistence_summary_report"]["ok"]
    assert reports["recovery_report"]["recovery"]["status"] == "recovered"


def test_entity_contracts_cover_records():
    for name in ("StorageRecord", "RepositoryRecord", "RegistryStorageRecord", "AuditStorageRecord",
                 "LineageStorageRecord", "ExecutionStorageRecord", "PersistenceRecord",
                 "PersistenceReadinessRecord"):
        assert name in ENTITY_CONTRACTS
    ok, missing = validate_entity("StorageRecord", {
        "storage_id": "s", "namespace": "registry", "key": "k", "checksum": "c", "fingerprint": "f",
        "uri": "file://x"})
    assert ok and missing == []


# =============================================================================
# Cross-run determinism (NR-9/NR-10)
# =============================================================================
def test_cross_run_determinism(eeg_fixtures, tmp_path):
    def run(sub):
        tracker, _, state, svc, out = _persisted(eeg_fixtures, tmp_path / sub)
        return out.record
    a, b = run("a"), run("b")
    assert a.persistence_id == b.persistence_id
    assert a.version.version == b.version.version
    assert a.identity.snapshot_fingerprint == b.identity.snapshot_fingerprint


# =============================================================================
# Missing / corrupted state
# =============================================================================
def test_recover_missing_snapshot_raises(eeg_fixtures, tmp_path):
    _, _, _, svc, out = _persisted(eeg_fixtures, tmp_path)
    svc2 = PersistencePlatformService(storage_root=svc.storage_root, lineage_tracker=LineageTracker())
    with pytest.raises(StorageError):
        svc2.recover("persistence_record+" + "0" * 16)


def test_corrupted_storage_object_detected(eeg_fixtures, tmp_path):
    _, _, _, svc, out = _persisted(eeg_fixtures, tmp_path)
    # corrupt one persisted registry object on disk; integrity must detect it
    eng = svc.engine
    key = svc._context[out.record.persistence_id]["storage_records"][0].key
    ns = svc._context[out.record.persistence_id]["storage_records"][0].namespace
    with open(eng._path(ns, key), "a") as fh:
        fh.write(" ")
    report = svc.integrity(out.record)
    assert not report.ok
    assert any(c.name == "storage_integrity" and not c.passed for c in report.checks)
