"""Final validation for DRP-4 — Persistence Platform.

Verifies the directive's 15 criteria against the real subsystem, driving the **real** P1->P3
pipeline + model-foundation training + serving over the committed EEG fixtures (no
replacement systems), persisting + recovering the platform state.

    python -m scripts.verify_drp4_persistence_platform
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    from ml.lineage import LineageTracker
    from backend.persistence_platform import (
        PersistencePlatformService, PersistenceStatus, RecoveryStatus, ReadinessClass, Repository,
        RepositoryKind, StorageEngine,
    )
    from _eeg_fixtures import generate_fixtures
    from _drp4_helpers import build_platform_state

    build_dir = pathlib.Path(tempfile.mkdtemp(prefix="drp4_build_"))
    eeg = generate_fixtures(str(build_dir / "fix"))
    tracker, ctx, state = build_platform_state(eeg, build_dir)
    store_root = str(pathlib.Path(tempfile.mkdtemp(prefix="drp4_store_")))
    svc = PersistencePlatformService(storage_root=store_root, lineage_tracker=tracker)
    out = svc.persist(state)
    record = out.record

    # --- 1. storage works ---
    try:
        eng = StorageEngine(store_root)
        srs = svc._context[record.persistence_id]["storage_records"]
        ok = len(srs) > 0 and all(eng.verify(sr) for sr in srs)
        check("1. Storage works", ok, f"{len(srs)} durable, checksum-verified objects")
    except Exception as exc:
        check("1. Storage works", False, f"error: {exc}")

    # --- 2. repositories work ---
    try:
        repo = Repository(StorageEngine(store_root), RepositoryKind.MODEL)
        ok = ctx["model"].model_id in repo.list_ids() and bool(repo.load(ctx["model"].model_id))
        check("2. Repositories work", ok, f"model repo holds {len(repo.list_ids())} record(s)")
    except Exception as exc:
        check("2. Repositories work", False, f"error: {exc}")

    # --- 3. registry persistence works ---
    try:
        names = {r.registry_name for r in record.registry_storage}
        ok = {"model_registry", "dataset_registry", "serving_registry"} <= names
        check("3. Registry persistence works", ok, f"registries={sorted(names)}")
    except Exception as exc:
        check("3. Registry persistence works", False, f"error: {exc}")

    # --- 4. audit persistence works ---
    try:
        ok = len(record.audit_storage) > 0 and all(a.head for a in record.audit_storage)
        check("4. Audit persistence works", ok,
              f"logs={[a.log_name for a in record.audit_storage]}")
    except Exception as exc:
        check("4. Audit persistence works", False, f"error: {exc}")

    # --- 5. lineage persistence works ---
    try:
        ok = record.lineage_storage.n_nodes > 0 and record.lineage_storage.n_edges > 0
        check("5. Lineage persistence works", ok,
              f"nodes={record.lineage_storage.n_nodes} edges={record.lineage_storage.n_edges}")
    except Exception as exc:
        check("5. Lineage persistence works", False, f"error: {exc}")

    # --- 6. recovery works (cold restart) ---
    try:
        fresh = PersistencePlatformService(storage_root=store_root, lineage_tracker=LineageTracker())
        rec = fresh.recover(record.persistence_id)
        ok = (rec.status == RecoveryStatus.RECOVERED and rec.anchor_verified
              and set(rec.registries) == {"model_registry", "dataset_registry", "serving_registry"}
              and all(lg.verify() for lg in rec.audit_logs.values())
              and rec.lineage_tracker.verify_chain(rec.lineage_id))
        check("6. Recovery works", ok,
              f"status={rec.status.value} registries={sorted(rec.registries)}")
    except Exception as exc:
        check("6. Recovery works", False, f"error: {exc}")

    # --- 7. validation works ---
    try:
        report = svc.integrity(record)
        check("7. Validation works", report.ok,
              "all integrity checks pass" if report.ok else
              f"failed={[c.name for c in report.failures()]}")
    except Exception as exc:
        check("7. Validation works", False, f"error: {exc}")

    # --- 8. readiness works ---
    try:
        ok = out.readiness.classification == ReadinessClass.READY and len(out.readiness.dimensions) == 6
        check("8. Readiness works", ok, f"classification={out.readiness.classification.value}")
    except Exception as exc:
        check("8. Readiness works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = svc.reports(record)
        expected = {"storage_report", "registry_report", "audit_persistence_report",
                    "lineage_persistence_report", "recovery_report", "validation_report",
                    "readiness_report", "persistence_summary_report"}
        check("9. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. determinism preserved ---
    try:
        build2 = pathlib.Path(tempfile.mkdtemp(prefix="drp4_build2_"))
        tracker2, _ctx2, state2 = build_platform_state(eeg, build2)
        svc2 = PersistencePlatformService(
            storage_root=str(pathlib.Path(tempfile.mkdtemp(prefix="drp4_store2_"))),
            lineage_tracker=tracker2)
        out2 = svc2.persist(state2)
        ok = (out.record.persistence_id == out2.record.persistence_id
              and out.record.version.version == out2.record.version.version)
        check("12. Determinism preserved", ok, "same persistence id + version across instances")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. persistence traceability preserved ---
    try:
        kinds = {n.kind for n in tracker.chain(record.lineage_id)}
        required = {"patient", "case", "feature", "dataset", "model", "prediction",
                    "serving_execution", "serving_response", "persistence_record"}
        ok = required <= kinds and tracker.verify_chain(record.lineage_id)
        check("13. Persistence traceability preserved", ok, f"kinds>={sorted(required)}")
    except Exception as exc:
        check("13. Persistence traceability preserved", False, f"error: {exc}")

    # --- 14. recovery integrity preserved ---
    try:
        fresh = PersistencePlatformService(storage_root=store_root, lineage_tracker=LineageTracker())
        rec = fresh.recover(record.persistence_id)
        kinds = {n.kind for n in rec.lineage_tracker.chain(rec.lineage_id)}
        ok = (rec.anchor_verified and "recovery_event" in kinds and "persistence_record" in kinds
              and all(p for _, p, _ in rec.checks))
        check("14. Recovery integrity preserved", ok,
              f"anchor_verified={rec.anchor_verified} recovery_event_in_chain={'recovery_event' in kinds}")
    except Exception as exc:
        check("14. Recovery integrity preserved", False, f"error: {exc}")

    # --- 15. persistence platform completed ---
    try:
        ok = (out.accepted and record.status == PersistenceStatus.PERSISTED
              and out.recovery.status == RecoveryStatus.RECOVERED
              and out.readiness.classification == ReadinessClass.READY and svc.integrity(record).ok)
        check("15. Persistence platform completed", ok,
              "persist -> recover -> validate -> score readiness, all green")
    except Exception as exc:
        check("15. Persistence platform completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_persistence_platform.py",
                               "tests/test_persistence_platform_e2e.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("10. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("10. Tests pass", False, f"error: {exc}")

    # --- 11. repository boundaries preserved ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_boundaries.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Repository boundaries preserved", False, f"error: {exc}")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDRP-4 — PERSISTENCE PLATFORM — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("PERSISTENCE:",
          f"status={record.status.value} readiness={out.readiness.classification.value} "
          f"recovery={out.recovery.status.value}")
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
