"""Final validation for DRP-6 — Clinical Validation & Evidence Platform.

Verifies the directive's 15 criteria against the real subsystem, driving the **real** P1->P3
pipeline + the reused DRP-2 production models over the committed EEG fixtures (no replacement
systems), generating benchmark / reliability / calibration / evidence + readiness.

    python -m scripts.verify_drp6_clinical_validation
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def _cohort(tmp: pathlib.Path):
    sys.path.insert(0, str(REPO / "tests"))
    from _eeg_fixtures import generate_fixtures
    from _drp6_helpers import build_feature_cohort
    return build_feature_cohort(generate_fixtures(str(tmp / "fix")), tmp)


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    from backend.clinical_validation import ClinicalValidationService, ValidationStatus, ReadinessClass
    from backend.production_models import PRODUCTION_ARCHITECTURES

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="drp6_verify_"))
    tracker, feats = _cohort(tmp)
    cv = ClinicalValidationService(lineage_tracker=tracker)
    run = cv.run_validation(feats)
    rep = next(iter(run.models.values()))
    record = rep.record

    # --- 1. benchmarking works ---
    try:
        required = {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "sensitivity",
                    "specificity", "ece", "brier"}
        ok = all(required <= set(o.benchmark.deterministic_metrics) for o in run.models.values())
        check("1. Benchmarking works", ok and len(run.models) == len(PRODUCTION_ARCHITECTURES),
              f"models={len(run.models)}")
    except Exception as exc:
        check("1. Benchmarking works", False, f"error: {exc}")

    # --- 2. calibration works ---
    try:
        ok = all(o.calibration.expected_calibration_error >= 0.0
                 and "n_bins" in o.calibration.confidence_distribution for o in run.models.values())
        check("2. Calibration works", ok, "ECE/Brier + confidence distribution + reliability curve")
    except Exception as exc:
        check("2. Calibration works", False, f"error: {exc}")

    # --- 3. reliability analysis works ---
    try:
        ok = all(o.reliability.repeatable and o.reliability.reproducible
                 and 0.0 <= o.reliability.reliability_score <= 1.0
                 and len(o.reliability.failure_modes) >= 2 for o in run.models.values())
        check("3. Reliability analysis works", ok,
              "repeatability/reproducibility/cross-run/cross-dataset/failure-modes")
    except Exception as exc:
        check("3. Reliability analysis works", False, f"error: {exc}")

    # --- 4. comparison works ---
    try:
        ok = (run.comparison is not None and run.comparison.n_models == len(run.models)
              and run.comparison.recommended_model in {o.record.model_id for o in run.models.values()})
        check("4. Comparison works", ok, f"recommended={run.comparison.recommended_model[:24]}")
    except Exception as exc:
        check("4. Comparison works", False, f"error: {exc}")

    # --- 5. evidence registry works ---
    try:
        counts = cv.registry.counts()
        ok = (all(cv.registry.exists(o.record.validation_id) for o in run.models.values())
              and cv.registry.orphans() == [] and counts["evidence"] == len(run.models)
              and counts["validation"] == len(run.models))
        check("5. Evidence registry works", ok, f"counts={counts} orphans={len(cv.registry.orphans())}")
    except Exception as exc:
        check("5. Evidence registry works", False, f"error: {exc}")

    # --- 6. readiness works ---
    try:
        classes = sorted({o.readiness.classification.value for o in run.models.values()})
        ok = all(o.readiness.classification == ReadinessClass.READY for o in run.models.values())
        check("6. Readiness works", ok, f"classes={classes}")
    except Exception as exc:
        check("6. Readiness works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        log = cv.audit_log_for(record.validation_id)
        ok = log.verify() and record.audit_head == log.head and len(log) >= 6
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        kinds = {n.kind for n in tracker.chain(record.lineage_id)}
        required_kinds = {"patient", "dataset", "model", "validation_benchmark",
                          "validation_evaluation", "validation_evidence", "validation_readiness"}
        ok = required_kinds <= kinds and tracker.verify_chain(record.lineage_id)
        check("8. Lineage integration works", ok, f"kinds>={sorted(required_kinds)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = cv.reports(record)
        expected = {"benchmark_report", "performance_report", "calibration_report",
                    "reliability_report", "comparison_report", "evidence_report", "readiness_report",
                    "audit_report", "lineage_report", "clinical_validation_summary"}
        check("9. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. determinism preserved (two validation runs over the SAME feature cohort, so the
    #     content-addressed models are identical -- isolates the validation layer's determinism
    #     from the pre-existing upstream cohort-rebuild flake documented in ADR-0027) ---
    try:
        a = ClinicalValidationService(lineage_tracker=tracker).run_validation(feats)
        b = ClinicalValidationService(lineage_tracker=tracker).run_validation(feats)
        ok = all(a.models[k].record.validation_id == b.models[k].record.validation_id
                 and a.models[k].record.version.version == b.models[k].record.version.version
                 for k in a.models)
        check("12. Determinism preserved", ok, "same validation id + version across runs")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. evidence traceability preserved ---
    try:
        ok = all(cv.integrity(o.record).ok and tracker.verify_chain(o.record.lineage_id)
                 for o in run.models.values())
        check("13. Evidence traceability preserved", ok,
              "every evidence chain verifies + integrity passes")
    except Exception as exc:
        check("13. Evidence traceability preserved", False, f"error: {exc}")

    # --- 14. validation readiness works ---
    try:
        ok = all(0.0 <= o.readiness.score <= 1.0 and len(o.readiness.dimensions) == 7
                 for o in run.models.values())
        check("14. Validation readiness works",
              ok, f"scores={sorted({o.readiness.score for o in run.models.values()})}")
    except Exception as exc:
        check("14. Validation readiness works", False, f"error: {exc}")

    # --- 15. clinical validation platform completed ---
    try:
        ok = (len(run.models) == len(PRODUCTION_ARCHITECTURES)
              and all(o.record.status == ValidationStatus.VALIDATED
                      and o.readiness.classification == ReadinessClass.READY
                      for o in run.models.values()))
        check("15. Clinical validation platform completed", ok,
              "benchmark -> evaluate -> reliability -> calibration -> evidence -> trace -> score")
    except Exception as exc:
        check("15. Clinical validation platform completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_clinical_validation.py",
                               "tests/test_clinical_validation_e2e.py"], cwd=str(REPO),
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
    print("\nDRP-6 — CLINICAL VALIDATION & EVIDENCE PLATFORM — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("MODELS:", ", ".join(f"{a}={run.models[a].readiness.classification.value}"
                               for a in sorted(run.models)))
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
