"""Final validation for Track 2 — Real Model Training & Benchmark Program.

Verifies the directive's 15 criteria against the **real** Real Model Training Platform and a
**real, locally-present EEG corpus** (CHB-MIT from PhysioNet — open access, no account). The
script acquires the minimal real subset if it is not already present (network on first run;
reuses local files thereafter), windows it into labelled samples, trains the platform's five
architectures on that real data, evaluates + benchmarks + compares them, and proves at least
one production-candidate model is objectively classified ``READY_FOR_SERVING`` — using actual
EEG recordings, not synthetic fixtures.

    python -m scripts.verify_track2_real_models

Set NV_TRACK1_NO_DOWNLOAD=1 to forbid network (then the corpus must already be local).
"""

from __future__ import annotations

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
    from backend.dataset_acquisition import DatasetSource as T1Src
    from backend.real_model_training import (
        ALL_ARCHITECTURES, EntityKind, RealModelTrainingService, ServingReadinessClass,
    )

    allow_download = os.environ.get("NV_TRACK1_NO_DOWNLOAD") not in ("1", "true", "True")
    svc = RealModelTrainingService()
    out = svc.develop(T1Src.CHB_MIT, allow_download=allow_download,
                      window_seconds=4.0, background_per_seizure=4)
    ds = out.dataset_record

    # --- 1. real dataset training works ---
    try:
        ok = (ds.source == "chb_mit" and ds.n_windows >= 1
              and len(out.candidates) == len(ALL_ARCHITECTURES)
              and all(c.training_run_id and c.reproducible for c in out.candidates))
        check("1. Real dataset training works", ok,
              f"windows={ds.n_windows} models={len(out.candidates)} (real CHB-MIT)")
    except Exception as exc:
        check("1. Real dataset training works", False, f"error: {exc}")

    # --- 2. evaluation works ---
    try:
        keys = {"accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_macro",
                "pr_auc_macro", "ece", "brier", "sensitivity", "specificity"}
        ok = all(keys <= set(ev.metrics) for ev in out.evaluations) and bool(out.evaluations)
        check("2. Evaluation works", ok,
              f"models_evaluated={len(out.evaluations)} (incl. sensitivity/specificity)")
    except Exception as exc:
        check("2. Evaluation works", False, f"error: {exc}")

    # --- 3. benchmarking works ---
    try:
        ok = all({"accuracy", "f1_macro", "roc_auc_macro", "pr_auc_macro", "ece", "brier"}
                 <= set(b.deterministic_metrics) and "training_time_ms" in b.performance
                 for b in out.benchmarks) and bool(out.benchmarks)
        check("3. Benchmarking works", ok, f"benchmarks={len(out.benchmarks)}")
    except Exception as exc:
        check("3. Benchmarking works", False, f"error: {exc}")

    # --- 4. experiment tracking works ---
    try:
        ok = (len(out.experiments) == len(ALL_ARCHITECTURES)
              and all(e.training_run_id and e.model_id and e.benchmark_metrics
                      and e.reproducible for e in out.experiments))
        check("4. Experiment tracking works", ok, f"experiments={len(out.experiments)}")
    except Exception as exc:
        check("4. Experiment tracking works", False, f"error: {exc}")

    # --- 5. comparison works ---
    try:
        ok = (out.comparison is not None and out.comparison.n_models == len(ALL_ARCHITECTURES)
              and out.comparison.recommended_model in {c.model_id for c in out.candidates})
        check("5. Comparison works", ok,
              f"recommended={out.comparison.recommended_model[:24] if out.comparison else None}")
    except Exception as exc:
        check("5. Comparison works", False, f"error: {exc}")

    # --- 6. readiness scoring works ---
    try:
        ready = out.ready_models()
        ok = bool(ready) and all(c.readiness_class == ServingReadinessClass.READY_FOR_SERVING
                                 for c in ready)
        check("6. Readiness scoring works", ok,
              f"ready_for_serving={len(ready)}/{len(out.candidates)}")
    except Exception as exc:
        check("6. Readiness scoring works", False, f"error: {exc}")

    # --- 7. registry integration works ---
    try:
        counts = svc.registry.counts()
        ok = (svc.registry.orphans() == [] and counts[EntityKind.MODEL.value] >= 1
              and counts[EntityKind.BENCHMARK.value] >= 1
              and counts[EntityKind.READINESS.value] >= 1)
        check("7. Registry integration works", ok, f"counts={counts} orphans=0")
    except Exception as exc:
        check("7. Registry integration works", False, f"error: {exc}")

    # --- 8. audit integration works ---
    try:
        log = svc.audit_log_for(out.dataset_id)
        ok = log.verify() and len(log) >= 5
        check("8. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("8. Audit integration works", False, f"error: {exc}")

    # --- 9. lineage integration works ---
    try:
        best = out.best_ready_model() or out.candidates[0]
        rnode = next((r.lineage_id for r in out.readinesses if r.model_id == best.model_id),
                     out.readinesses[0].lineage_id)
        kinds = {n.kind for n in svc.lineage.chain(rnode)}
        required = {"training_dataset", "training_recording", "training_feature_asset",
                    "training_run", "trained_model", "model_evaluation", "model_benchmark",
                    "readiness_assessment"}
        ok = required <= kinds and svc.lineage.verify_chain(rnode) and \
            {"real_dataset", "dataset_source"} <= kinds
        check("9. Lineage integration works", ok, f"chain_kinds={len(kinds)} reaches source")
    except Exception as exc:
        check("9. Lineage integration works", False, f"error: {exc}")

    # --- 10. reports generate ---
    try:
        reports = svc.reports(out)
        expected = {"training_report", "evaluation_report", "benchmark_report",
                    "comparison_report", "readiness_report", "registry_report", "audit_report",
                    "lineage_report", "model_summary_report"}
        check("10. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("10. Reports generate", False, f"error: {exc}")

    # --- 13. determinism preserved ---
    try:
        out2 = RealModelTrainingService().develop(T1Src.CHB_MIT, allow_download=False,
                                                  window_seconds=4.0, background_per_seizure=4)
        am = {c.architecture: c.headline_metrics for c in out.candidates}
        bm = {c.architecture: c.headline_metrics for c in out2.candidates}
        ok = out.dataset_id == out2.dataset_id and am == bm
        check("13. Determinism preserved", ok, "same dataset id + metrics across instances")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. real model evidence exists ---
    try:
        best = out.best_ready_model() or out.candidates[0]
        hm = best.headline_metrics
        ok = (ds.source == "chb_mit" and ds.n_windows >= 1 and best.reproducible
              and best.validation.ok and "accuracy" in hm and "roc_auc_macro" in hm)
        check("14. Real model evidence exists", ok,
              f"best={best.architecture.value} acc={hm.get('accuracy'):.3f} "
              f"roc_auc={hm.get('roc_auc_macro'):.3f} (real EEG)")
    except Exception as exc:
        check("14. Real model evidence exists", False, f"error: {exc}")

    # --- 15. Track 2 completed (>=1 model READY_FOR_SERVING on real data) ---
    try:
        best = out.best_ready_model()
        ok = (best is not None and best.ready_for_serving and ds.source == "chb_mit"
              and ds.n_windows >= 1)
        check("15. Track 2 completed", ok,
              "real CHB-MIT trained -> evaluated -> benchmarked -> compared -> READY_FOR_SERVING")
    except Exception as exc:
        check("15. Track 2 completed", False, f"error: {exc}")

    # --- 11. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_real_model_training.py", "tests/test_real_model_training_e2e.py"],
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
    print("\nTRACK 2 — REAL MODEL TRAINING & BENCHMARK — FINAL VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 66)
    best = out.best_ready_model() or (out.candidates[0] if out.candidates else None)
    if best is not None:
        print(f"BEST CANDIDATE: {best.architecture.value}  model={best.model_id}")
        print(f"  classification={best.readiness_class.value}  metrics={ {k: round(v,3) for k,v in best.headline_metrics.items()} }")
    print(f"DATASET: real CHB-MIT  windows={ds.n_windows}  "
          f"classes={ds.class_distribution}  split={ds.split_strategy.value}")
    print("-" * 66)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
