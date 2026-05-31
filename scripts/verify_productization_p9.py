"""Final validation for Productization P9 — Validation & Performance Assurance Program.

Objectively verifies the directive's 15 phase-completion criteria: NeuroVision is now
**measurable**. Runs the full validation program over the real P1-P8 systems and checks
that benchmarking/performance/reliability/robustness/calibration/drift/scorecards/reports
all work, that determinism + traceability are preserved, that existing systems are
unchanged (validation is evaluation-only, one-way), and that product validation completed.

    python -m scripts.verify_productization_p9
"""

from __future__ import annotations

import ast
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

    import _eeg_fixtures as fx
    from validation import run_validation

    tmp = tempfile.mkdtemp(prefix="nv_p9_verify_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))
    vrun = run_validation(fixtures, benchmark_runs=3, reliability_repeats=3, reliability_stress=5,
                          cross_instance=True, workspace_dir=str(pathlib.Path(tmp) / "ws"))

    # --- 1. benchmarking works ---
    try:
        bms = vrun["benchmarks"]
        ok = (set(bms) == {"pipeline", "inference", "workflow", "operational"}
              and all(b.to_dict()["success_rate"] == 1.0 and b.to_dict()["deterministic"]
                      for b in bms.values()))
        check("1. Benchmarking works", ok, f"benchmarks={sorted(bms)}")
    except Exception as exc:
        check("1. Benchmarking works", False, f"error: {exc}")

    # --- 2. performance validation works ---
    try:
        perf = vrun["performance"]
        check("2. Performance validation works", perf["ok"], f"checks={len(perf['checks'])}")
    except Exception as exc:
        check("2. Performance validation works", False, f"error: {exc}")

    # --- 3. reliability validation works ---
    try:
        rel = vrun["reliability"]
        check("3. Reliability validation works", rel["ok"],
              f"checks={[c['name'] for c in rel['checks'] if not c['passed']] or 'all pass'}")
    except Exception as exc:
        check("3. Reliability validation works", False, f"error: {exc}")

    # --- 4. robustness validation works ---
    try:
        rob = vrun["robustness"]
        check("4. Robustness validation works", rob["ok"],
              f"graceful={rob['all_graceful']} recovered={rob['recovered']} cases={rob['n_cases']}")
    except Exception as exc:
        check("4. Robustness validation works", False, f"error: {exc}")

    # --- 5. calibration validation works ---
    try:
        cal = vrun["calibration"]
        check("5. Calibration validation works", cal["ok"], f"models={len(cal['models'])}")
    except Exception as exc:
        check("5. Calibration validation works", False, f"error: {exc}")

    # --- 6. drift analysis works ---
    try:
        drift = vrun["drift"]
        ok = drift["pipeline_drift"]["stable"] and "feature_drift" in drift and "model_consistency" in drift
        check("6. Drift analysis works", ok,
              f"feature_l1={drift['feature_drift']['l1']:.3f} stable={drift['pipeline_drift']['stable']}")
    except Exception as exc:
        check("6. Drift analysis works", False, f"error: {exc}")

    # --- 7. scorecards generate ---
    try:
        sc = vrun["scorecards"]
        ok = len(sc["scorecards"]) == 9 and "overall_product_readiness" in sc["scorecards"]
        check("7. Scorecards generate", ok, f"n={len(sc['scorecards'])} overall_ready={sc['overall_ready']}")
    except Exception as exc:
        check("7. Scorecards generate", False, f"error: {exc}")

    # --- 8. reports generate ---
    try:
        reports = vrun["reports"]
        expected = {"benchmark_report", "performance_report", "reliability_report",
                    "robustness_report", "calibration_report", "drift_report", "readiness_report",
                    "validation_summary", "executive_summary"}
        check("8. Reports generate", expected <= set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("8. Reports generate", False, f"error: {exc}")

    # --- 10. existing systems remain unchanged (validation is one-way, evaluation-only) ---
    try:
        leaks = []
        for pkg in ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend",
                    "operations"):
            for path in (REPO / pkg).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    roots = set()
                    if isinstance(node, ast.Import):
                        roots = {a.name.split(".")[0] for a in node.names}
                    elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                        roots = {node.module.split(".")[0]}
                    if "validation" in roots:
                        leaks.append(str(path.relative_to(REPO)))
        check("10. Existing systems remain unchanged", not leaks,
              "validation is evaluation-only; no domain package imports it")
    except Exception as exc:
        check("10. Existing systems remain unchanged", False, f"error: {exc}")

    # --- 12. determinism preserved ---
    try:
        repro = vrun["reproducibility"]
        ok = repro["ok"] and repro["within_instance"]["reproducible"] and \
            repro.get("cross_instance", {}).get("reproducible")
        check("12. Determinism preserved", ok,
              f"within={repro['within_instance']['reproducible']} "
              f"cross={repro.get('cross_instance', {}).get('reproducible')}")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. validation traceability preserved ---
    try:
        res = vrun["pipeline_result"]
        rel = vrun["reliability"]
        lineage_ok = res.traceable and any(
            c["name"] == "lineage_integrity" and c["passed"] for c in rel["checks"])
        check("13. Validation traceability preserved", lineage_ok,
              "prediction chain verifies to the patient")
    except Exception as exc:
        check("13. Validation traceability preserved", False, f"error: {exc}")

    # --- 14. readiness scoring works ---
    try:
        sc = vrun["scorecards"]
        ok = all("score" in c and "ready" in c for c in sc["scorecards"].values()) \
            and isinstance(sc["overall_score"], float)
        check("14. Readiness scoring works", ok, f"overall_score={sc['overall_score']:.3f}")
    except Exception as exc:
        check("14. Readiness scoring works", False, f"error: {exc}")

    # --- 15. product validation completed ---
    try:
        check("15. Product validation completed", vrun["validation_complete"],
              f"executive_summary present={bool(vrun['reports'].get('executive_summary'))}")
    except Exception as exc:
        check("15. Product validation completed", False, f"error: {exc}")

    # --- 9. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_validation.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("9. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("9. Tests pass", False, f"error: {exc}")

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
    print("\nPRODUCTIZATION P9 — VALIDATION & PERFORMANCE ASSURANCE — FINAL VALIDATION")
    print("=" * 72)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 72)
    # A compact executive snapshot (the evidence P9 exists to produce).
    exe = vrun["reports"]["executive_summary"]
    acc = exe["how_accurate_are_the_models"]
    print("EXECUTIVE SNAPSHOT:")
    print("  models (acc): " + ", ".join(
        f"{a}={m['accuracy']:.2f}" for a, m in acc["per_architecture"].items()))
    print(f"  reliable={exe['how_reliable_is_the_pipeline']['reliable']} "
          f"robust={exe['how_robust_is_the_system']['graceful_on_bad_input']} "
          f"stable={exe['how_stable_are_predictions']['pipeline_stable']} "
          f"ready={exe['how_ready_is_the_product']['overall_ready']}")
    print("-" * 72)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
