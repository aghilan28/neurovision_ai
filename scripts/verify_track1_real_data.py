"""Final validation for Track 1 — Real Data Acquisition & Integration Program.

Verifies the directive's 15 criteria against the **real** Real Dataset Platform and a
**real, locally-present EEG corpus**. CHB-MIT (PhysioNet, open access, no account) is the
proof corpus: the script acquires the minimal real subset if it is not already present
(requires network on first run; reuses the local files thereafter), then proves it is
``READY_FOR_TRAINING`` end to end — using actual EEG recordings, not synthetic fixtures.

    python -m scripts.verify_track1_real_data

Set NV_TRACK1_NO_DOWNLOAD=1 to forbid network (then the corpus must already be local).
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    from backend.dataset_acquisition import (
        AvailabilityState, DatasetSource, EntityKind, LabelScheme, RealDatasetService,
        TrainingReadinessClass, all_specs,
    )

    svc = RealDatasetService()

    # --- acquire the real CHB-MIT subset (only if missing) -------------------
    allow_download = os.environ.get("NV_TRACK1_NO_DOWNLOAD") not in ("1", "true", "True")
    acq = svc.acquire(DatasetSource.CHB_MIT, allow_download=allow_download, timeout=300.0)

    # full real integration
    out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
    result = out.connector_result

    # --- 1. dataset discovery works ---
    try:
        ok = len(result.discovered_files) >= 1 and all(r.parse_ok for r in result.recordings)
        check("1. Dataset discovery works", ok,
              f"discovered={len(result.discovered_files)} recordings={len(result.recordings)}")
    except Exception as exc:
        check("1. Dataset discovery works", False, f"error: {exc}")

    # --- 2. dataset validation works ---
    try:
        ok = out.validation.ok and out.validation.n_checks == 9
        check("2. Dataset validation works", ok,
              f"ok={out.validation.ok} checks={out.validation.n_checks}")
    except Exception as exc:
        check("2. Dataset validation works", False, f"error: {exc}")

    # --- 3. metadata extraction works ---
    try:
        ok = all(r.sampling_frequency > 0 and r.n_channels > 0 and r.duration_seconds > 0
                 for r in result.recordings) and bool(result.recordings)
        check("3. Metadata extraction works", ok,
              f"sfreq={sorted({r.sampling_frequency for r in result.recordings})} "
              f"channels={sorted({r.n_channels for r in result.recordings})}")
    except Exception as exc:
        check("3. Metadata extraction works", False, f"error: {exc}")

    # --- 4. label extraction works (REAL labels, no synthetic) ---
    try:
        lv = out.label_verification
        ok = (lv.scheme == LabelScheme.CHB_MIT_SEIZURE and lv.coverage == 1.0
              and lv.n_classes >= 2 and lv.consistent)
        check("4. Label extraction works", ok,
              f"scheme={lv.scheme.value} coverage={lv.coverage} classes={list(lv.classes)}")
    except Exception as exc:
        check("4. Label extraction works", False, f"error: {exc}")

    # --- 5. inventory generation works ---
    try:
        inv = out.inventory
        ok = inv.n_recordings >= 1 and inv.n_patients >= 1 and inv.n_labels >= 1
        check("5. Inventory generation works", ok,
              f"recordings={inv.n_recordings} patients={inv.n_patients} labels={inv.n_labels}")
    except Exception as exc:
        check("5. Inventory generation works", False, f"error: {exc}")

    # --- 6. registry integration works ---
    try:
        counts = svc.registry.counts()
        ok = (svc.registry.orphans() == [] and counts[EntityKind.DATASET.value] == 1
              and counts[EntityKind.RECORDING.value] >= 1 and counts[EntityKind.LABEL.value] >= 1)
        check("6. Registry integration works", ok,
              f"counts={counts} orphans={len(svc.registry.orphans())}")
    except Exception as exc:
        check("6. Registry integration works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        log = svc.audit_log_for(out.dataset_id)
        ok = log.verify() and out.dataset_record.audit_head == log.head and len(log) >= 5
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        kinds = {n.kind for n in svc.lineage.chain(out.registry_lineage_id)}
        required = {"dataset_source", "real_dataset", "dataset_patient", "dataset_recording",
                    "dataset_label", "dataset_registry"}
        ok = required <= kinds and svc.lineage.verify_chain(out.registry_lineage_id)
        check("8. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. readiness scoring works ---
    try:
        ok = (0.0 <= out.readiness.score <= 1.0 and out.readiness.dimensions
              and out.readiness.classification == TrainingReadinessClass.READY_FOR_TRAINING)
        check("9. Readiness scoring works", ok,
              f"class={out.readiness.classification.value} score={out.readiness.score}")
    except Exception as exc:
        check("9. Readiness scoring works", False, f"error: {exc}")

    # --- 10. reports generate ---
    try:
        reports = svc.reports(out)
        expected = {"acquisition_report", "validation_report", "inventory_report", "label_report",
                    "metadata_report", "readiness_report", "audit_report", "lineage_report",
                    "dataset_summary_report"}
        check("10. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("10. Reports generate", False, f"error: {exc}")

    # --- 13. determinism preserved ---
    try:
        out2 = RealDatasetService().integrate(DatasetSource.CHB_MIT, allow_download=False)
        ok = (out.dataset_id == out2.dataset_id and out.readiness.score == out2.readiness.score
              and out.dataset_record.content_fingerprint == out2.dataset_record.content_fingerprint)
        check("13. Determinism preserved", ok, "same dataset id + fingerprint + readiness")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. real dataset support exists ---
    try:
        specs = {s.source for s in all_specs()}
        real = (out.availability.state in (AvailabilityState.VERIFIED, AvailabilityState.READY)
                and out.dataset_record.n_recordings >= 1
                and all(r.parse_ok for r in result.recordings)
                and out.label_verification.scheme != LabelScheme.NONE)
        ok = real and len(specs) == 5
        check("14. Real dataset support exists", ok,
              f"availability={out.availability.state.value} acquired={acq.n_acquired} "
              f"real_recordings={out.dataset_record.n_recordings}")
    except Exception as exc:
        check("14. Real dataset support exists", False, f"error: {exc}")

    # --- 15. Track 1 completed (>=1 real dataset READY_FOR_TRAINING) ---
    try:
        ok = (out.ready_for_training and out.label_verification.coverage == 1.0
              and out.dataset_record.n_recordings >= 1
              and out.availability.state in (AvailabilityState.VERIFIED, AvailabilityState.READY))
        check("15. Track 1 completed", ok,
              "real CHB-MIT acquired, validated, labelled, inventoried, READY_FOR_TRAINING")
    except Exception as exc:
        check("15. Track 1 completed", False, f"error: {exc}")

    # --- 11. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_dataset_acquisition.py", "tests/test_dataset_acquisition_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_boundaries.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("12. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nTRACK 1 — REAL DATA ACQUISITION & INTEGRATION — FINAL VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 66)
    print(f"PROOF DATASET: CHB-MIT  source={out.source.value}  "
          f"recordings={out.dataset_record.n_recordings}  "
          f"labels={out.dataset_record.n_labels}  "
          f"classification={out.readiness.classification.value}")
    print("-" * 66)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
