"""Final validation for DRP-2 — Production Model Program.

Verifies the directive's 15 criteria against the real subsystem, driving the **real**
P1->P3 feature pipeline over the committed EEG fixtures (no replacement systems) and
developing every production architecture (EEGNet, DeepConvNet, Temporal CNN, Transformer
EEG, Hybrid EEG).

    python -m scripts.verify_drp2_production_models
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def _build_cohort(tmp: pathlib.Path):
    """Run P1 -> P2 -> P3 over the committed fixtures on one shared lineage tracker."""
    sys.path.insert(0, str(REPO / "tests"))
    from _eeg_fixtures import generate_fixtures
    from _drp2_helpers import build_feature_cohort
    eeg = generate_fixtures(str(tmp / "fix"))
    return build_feature_cohort(eeg, tmp)


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    from backend.production_models import (
        ProductionModelService, PRODUCTION_ARCHITECTURES, ModelStatus, ReadinessClass,
    )

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="drp2_verify_"))
    tracker, feats = _build_cohort(tmp)
    svc = ProductionModelService(lineage_tracker=tracker)
    outs = svc.develop_all(feats, dataset_key="cohort", seed=7)
    rep = next(iter(outs.values()))

    # --- 1. training works ---
    try:
        ok = all(o.experiment is not None and o.experiment.reproducible
                 and o.experiment.n_params > 0 for o in outs.values())
        check("1. Training works", ok and len(outs) == 5,
              f"architectures={sorted(outs)}")
    except Exception as exc:
        check("1. Training works", False, f"error: {exc}")

    # --- 2. benchmarking works ---
    try:
        required = {"accuracy", "precision_macro", "recall_macro", "f1_macro",
                    "roc_auc_macro", "pr_auc_macro", "ece", "brier"}
        perf = {"latency_ms_per_sample", "peak_memory_kb", "training_time_ms", "inference_time_ms"}
        ok = all(required <= set(o.benchmark.deterministic_metrics)
                 and perf <= set(o.benchmark.performance) for o in outs.values())
        check("2. Benchmarking works", ok, "8 deterministic metrics + 4 informational timings")
    except Exception as exc:
        check("2. Benchmarking works", False, f"error: {exc}")

    # --- 3. evaluation works ---
    try:
        ok = all(o.evaluation.confusion_matrix and "stability_score" in o.evaluation.stability_analysis
                 and o.evaluation.reliability_analysis["bins"] for o in outs.values())
        check("3. Evaluation works", ok,
              "confusion/calibration/error/class-distribution/stability/reliability")
    except Exception as exc:
        check("3. Evaluation works", False, f"error: {exc}")

    # --- 4. readiness works ---
    try:
        classes = sorted({o.readiness.classification.value for o in outs.values()})
        ok = all(o.readiness.classification == ReadinessClass.READY for o in outs.values())
        check("4. Readiness works", ok, f"classes={classes}")
    except Exception as exc:
        check("4. Readiness works", False, f"error: {exc}")

    # --- 5. registry integration works (shared dataset/model + production registry) ---
    try:
        counts = svc.production_registry.counts()
        shared_models = len(svc.model_registry.list_models())
        ok = (all(svc.production_registry.exists(o.model_id) and svc.model_registry.exists(o.model_id)
                  and svc.dataset_registry.exists(o.dataset_id) for o in outs.values())
              and svc.production_registry.orphans() == []
              and len(svc.dataset_registry.list_datasets()) == 1
              and shared_models == 5 and counts["production_model"] == 5)
        check("5. Registry integration works", ok,
              f"counts={counts} shared_models={shared_models} orphans={len(svc.production_registry.orphans())}")
    except Exception as exc:
        check("5. Registry integration works", False, f"error: {exc}")

    # --- 6. audit integration works ---
    try:
        log = svc.audit_log_for(rep.model.model_id)
        ok = log.verify() and rep.model.audit_head == log.head and len(log) >= 7
        check("6. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("6. Audit integration works", False, f"error: {exc}")

    # --- 7. lineage integration works ---
    try:
        kinds = {n.kind for n in tracker.chain(rep.readiness.lineage_id)}
        required_kinds = {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                          "training_run", "training_experiment", "model", "benchmark",
                          "readiness_assessment"}
        ok = required_kinds <= kinds and tracker.verify_chain(rep.readiness.lineage_id)
        check("7. Lineage integration works", ok, f"kinds>={sorted(required_kinds)}")
    except Exception as exc:
        check("7. Lineage integration works", False, f"error: {exc}")

    # --- 8. reports generate ---
    try:
        comparison = svc.compare(outs)
        reports = svc.reports(rep.model, comparison=comparison)
        expected = {"training_report", "benchmark_report", "evaluation_report", "comparison_report",
                    "readiness_report", "registry_report", "audit_report", "lineage_report",
                    "model_summary_report"}
        check("8. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("8. Reports generate", False, f"error: {exc}")

    # --- 11. determinism preserved (cross-instance) ---
    try:
        tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="drp2_verify2_"))
        tracker2, feats2 = _build_cohort(tmp2)
        svc2 = ProductionModelService(lineage_tracker=tracker2)
        outs2 = svc2.develop_all(feats2, dataset_key="cohort", seed=7)
        ok = all(outs[a].model.model_id == outs2[a].model.model_id
                 and outs[a].model.version.version == outs2[a].model.version.version
                 for a in outs)
        check("11. Determinism preserved", ok, "same model id + version across instances")
    except Exception as exc:
        check("11. Determinism preserved", False, f"error: {exc}")

    # --- 12. model traceability preserved ---
    try:
        ok = all(svc.integrity(o.model).ok for o in outs.values())
        check("12. Model traceability preserved", ok,
              "integrity (incl. lineage/traceability) passes for every model")
    except Exception as exc:
        check("12. Model traceability preserved", False, f"error: {exc}")

    # --- 13. benchmark traceability preserved ---
    try:
        ok = all(tracker.verify_chain(o.benchmark.lineage_id)
                 and {"benchmark", "model", "dataset", "feature", "patient"}
                 <= {n.kind for n in tracker.chain(o.benchmark.lineage_id)} for o in outs.values())
        check("13. Benchmark traceability preserved", ok, "benchmark chain reaches the patient")
    except Exception as exc:
        check("13. Benchmark traceability preserved", False, f"error: {exc}")

    # --- 14. readiness scoring works ---
    try:
        ok = all(0.0 <= o.readiness.score <= 1.0 and o.readiness.dimensions
                 and len(o.readiness.dimensions) == 7 for o in outs.values())
        check("14. Readiness scoring works", ok,
              f"scores={sorted({o.readiness.score for o in outs.values()})}")
    except Exception as exc:
        check("14. Readiness scoring works", False, f"error: {exc}")

    # --- 15. production model program completed ---
    try:
        ok = (len(outs) == 5
              and all(o.accepted and o.model.status == ModelStatus.CANDIDATE
                      and o.readiness.classification == ReadinessClass.READY for o in outs.values()))
        check("15. Production model program completed", ok,
              "all 5 architectures trained, evaluated, benchmarked, scored, traceable, audited")
    except Exception as exc:
        check("15. Production model program completed", False, f"error: {exc}")

    # --- 9. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_production_models.py",
                               "tests/test_production_models_e2e.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("9. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("9. Tests pass", False, f"error: {exc}")

    # --- 10. repository boundaries preserved ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_boundaries.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("10. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("10. Repository boundaries preserved", False, f"error: {exc}")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDRP-2 — PRODUCTION MODEL PROGRAM — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("ARCHITECTURES:",
          ", ".join(f"{a.value}={outs[a.value].readiness.classification.value}"
                    for a in PRODUCTION_ARCHITECTURES))
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
