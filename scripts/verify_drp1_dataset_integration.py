"""Final validation for DRP-1 — Real Dataset Integration Program.

Verifies the directive's 15 criteria against the real subsystem + the real built-in
manifests for the mandatory corpora (TUH EEG, CHB-MIT, Temple/TUSZ, Siena Scalp, Bonn).

    python -m scripts.verify_drp1_dataset_integration
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    from backend.dataset_integration import (
        DatasetIntegrationService, EegDatasetSource, InventoryStatus, ReadinessClass,
        GovernanceStatus, EntityKind,
    )

    svc = DatasetIntegrationService()
    MANDATORY = [EegDatasetSource.TUH_EEG, EegDatasetSource.CHB_MIT, EegDatasetSource.TEMPLE_EEG,
                 EegDatasetSource.SIENA_SCALP, EegDatasetSource.BONN]

    # --- 1. inventory works ---
    try:
        inv = svc.inventory()
        ok = {i.source for i in inv} >= set(MANDATORY) and all(
            i.status == InventoryStatus.INVENTORIED for i in inv)
        check("1. Inventory works", ok, f"n_datasets={len(inv)}")
    except Exception as exc:
        check("1. Inventory works", False, f"error: {exc}")

    # --- run the full registration once for the remaining checks ---
    outs = svc.register_all_mandatory()

    # --- 2. registration works ---
    try:
        ok = all(o.accepted for o in outs.values()) and len(outs) == 5
        check("2. Registration works", ok, f"registered={list(outs)}")
    except Exception as exc:
        check("2. Registration works", False, f"error: {exc}")

    # --- 3. validation works ---
    try:
        ok = all(o.validation.ok and o.validation.n_checks == 8 for o in outs.values())
        check("3. Validation works", ok, "8 checks per dataset; all valid")
    except Exception as exc:
        check("3. Validation works", False, f"error: {exc}")

    # --- 4. governance works ---
    try:
        ok = all(o.governance.status == GovernanceStatus.DOCUMENTED for o in outs.values())
        check("4. Governance works", ok, "license/attribution/source documented")
    except Exception as exc:
        check("4. Governance works", False, f"error: {exc}")

    # --- 5. readiness works ---
    try:
        ok = all(o.readiness.classification == ReadinessClass.READY for o in outs.values())
        check("5. Readiness works", ok,
              f"classes={sorted({o.readiness.classification.value for o in outs.values()})}")
    except Exception as exc:
        check("5. Readiness works", False, f"error: {exc}")

    # --- 6. registry integration works (incl. model-foundation cross-ref) ---
    try:
        counts = svc.registry.counts()
        mf_ok = all(outs[s].model_foundation_dataset_id for s in ("tuh_eeg", "chb_mit", "temple_eeg"))
        ok = (svc.registry.orphans() == [] and counts[EntityKind.DATASET.value] == 5 and mf_ok)
        check("6. Registry integration works", ok,
              f"counts={counts} mf_linked(tuh/chb/temple)={mf_ok} orphans={len(svc.registry.orphans())}")
    except Exception as exc:
        check("6. Registry integration works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        o = outs["chb_mit"]
        log = svc.audit_log_for(o.dataset_record.dataset_id)
        ok = log.verify() and o.dataset_record.audit_head == log.head and len(log) >= 5
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        o = outs["bonn"]
        kinds = {n.kind for n in svc.lineage.chain(o.lineage_id)}
        ok = {"dataset_source", "dataset", "dataset_version"} == kinds and svc.lineage.verify_chain(o.lineage_id)
        check("8. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = svc.reports(outs["tuh_eeg"])
        expected = {"inventory_report", "validation_report", "governance_report", "readiness_report",
                    "registry_report", "audit_report", "lineage_report", "dataset_summary_report"}
        check("9. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. determinism preserved ---
    try:
        s2 = DatasetIntegrationService()
        o2 = s2.register(source=EegDatasetSource.SIENA_SCALP)
        o1 = svc.register(source=EegDatasetSource.SIENA_SCALP)
        ok = (o1.dataset_record.dataset_id == o2.dataset_record.dataset_id
              and o1.readiness.score == o2.readiness.score)
        check("12. Determinism preserved", ok, "same dataset id + readiness across instances")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. dataset traceability preserved ---
    try:
        ok = all(svc.lineage.verify_chain(o.lineage_id) for o in outs.values())
        check("13. Dataset traceability preserved", ok, "Source -> Dataset -> Version verifies")
    except Exception as exc:
        check("13. Dataset traceability preserved", False, f"error: {exc}")

    # --- 14. dataset readiness scoring works ---
    try:
        ok = all(0.0 <= o.readiness.score <= 1.0 and o.readiness.dimensions for o in outs.values())
        check("14. Dataset readiness scoring works", ok,
              f"scores={sorted({o.readiness.score for o in outs.values()})}")
    except Exception as exc:
        check("14. Dataset readiness scoring works", False, f"error: {exc}")

    # --- 15. dataset integration completed ---
    try:
        ok = (len(outs) == 5 and all(o.accepted and o.readiness.classification == ReadinessClass.READY
                                     for o in outs.values()))
        check("15. Dataset integration completed", ok,
              "all 5 mandatory corpora inventoried, registered, validated, governed, READY")
    except Exception as exc:
        check("15. Dataset integration completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_dataset_integration.py"], cwd=str(REPO),
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
    print("\nDRP-1 — REAL DATASET INTEGRATION — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("MANDATORY DATASETS:",
          ", ".join(f"{s}={o.readiness.classification.value}" for s, o in outs.items()))
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
