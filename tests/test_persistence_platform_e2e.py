"""End-to-end test for DRP-4 — Persistence Platform.

Demonstrates the full required deliverable: persist registries -> persist audit history ->
persist lineage history -> persist execution history -> recover state (cold restart) ->
validate recovery -> score persistence readiness — built on the real DRP-1 datasets, DRP-2
models, and DRP-3 serving records, on one shared lineage tracker (no replacement systems).
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.persistence_platform import (
    PersistencePlatformService, PersistenceStatus, RecoveryStatus, ReadinessClass,
)

from _drp4_helpers import build_platform_state


def test_full_persistence_deliverable(eeg_fixtures, tmp_path):
    tracker, ctx, state = build_platform_state(eeg_fixtures, tmp_path / "build")
    svc = PersistencePlatformService(storage_root=str(tmp_path / "store"), lineage_tracker=tracker)

    out = svc.persist(state)
    assert out.accepted and out.reason == PersistenceStatus.PERSISTED.value
    assert out.readiness.classification == ReadinessClass.READY
    assert svc.integrity(out.record).ok

    # all eight reports
    reports = svc.reports(out.record)
    assert len(reports) == 8 and reports["persistence_summary_report"]["ok"]

    # cold restart: nothing in memory, everything reconstructed from disk
    fresh = PersistencePlatformService(storage_root=svc.storage_root, lineage_tracker=LineageTracker())
    rec = fresh.recover(out.record.persistence_id)
    assert rec.status == RecoveryStatus.RECOVERED and rec.anchor_verified
    # registries + audit + lineage + execution all came back
    assert set(rec.registries) == {"model_registry", "dataset_registry", "serving_registry"}
    assert all(lg.verify() for lg in rec.audit_logs.values())
    assert set(rec.execution_histories) == {"serving", "inference"}
    assert rec.lineage_tracker.verify_chain(rec.lineage_id)
    # the recovered model registry actually contains the served model
    assert ctx["model"].model_id in rec.registries["model_registry"]["models"]


def test_persistence_builds_on_drp1_drp2_drp3(eeg_fixtures, tmp_path):
    """The persisted snapshot carries the DRP-1 dataset registry, the DRP-2 model registry,
    and the DRP-3 serving registry — all reconstructable from durable storage."""
    tracker, ctx, state = build_platform_state(eeg_fixtures, tmp_path / "build")
    svc = PersistencePlatformService(storage_root=str(tmp_path / "store"), lineage_tracker=tracker)
    out = svc.persist(state)

    fresh = PersistencePlatformService(storage_root=svc.storage_root, lineage_tracker=LineageTracker())
    rec = fresh.recover(out.record.persistence_id)
    # DRP-2 model registry: the served model survives
    assert ctx["model"].model_id in rec.registries["model_registry"]["models"]
    # DRP-3 serving registry: the served execution survives
    serving_snapshot = rec.registries["serving_registry"]
    assert ctx["out"].execution.execution_id in serving_snapshot["executions"]
    # DRP-1/model-foundation dataset registry: the dataset survives
    assert len(rec.registries["dataset_registry"]["datasets"]) >= 1


def test_partial_recovery_is_graceful(eeg_fixtures, tmp_path):
    """A corrupted persisted component yields a PARTIAL recovery (graceful), never a crash."""
    tracker, ctx, state = build_platform_state(eeg_fixtures, tmp_path / "build")
    svc = PersistencePlatformService(storage_root=str(tmp_path / "store"), lineage_tracker=tracker)
    out = svc.persist(state)

    # corrupt the persisted lineage object on disk
    fresh = PersistencePlatformService(storage_root=svc.storage_root, lineage_tracker=LineageTracker())
    with open(fresh.engine._path("lineage", "graph"), "a") as fh:
        fh.write(" ")
    rec = fresh.recover(out.record.persistence_id)
    assert rec.status in (RecoveryStatus.PARTIAL, RecoveryStatus.FAILED)
    assert any(c[0] == "lineage_recovery" and not c[1] for c in rec.checks)  # detected, not crashed


def test_recovery_is_deterministic(eeg_fixtures, tmp_path):
    """Recovering twice from the same storage yields the same recovery id."""
    tracker, ctx, state = build_platform_state(eeg_fixtures, tmp_path / "build")
    svc = PersistencePlatformService(storage_root=str(tmp_path / "store"), lineage_tracker=tracker)
    out = svc.persist(state)
    a = PersistencePlatformService(storage_root=svc.storage_root,
                                   lineage_tracker=LineageTracker()).recover(out.record.persistence_id)
    b = PersistencePlatformService(storage_root=svc.storage_root,
                                   lineage_tracker=LineageTracker()).recover(out.record.persistence_id)
    assert a.recovery_id == b.recovery_id and a.status == b.status
