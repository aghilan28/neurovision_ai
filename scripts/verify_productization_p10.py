"""Final validation for Productization P10 — Deployment Readiness & Production Certification.

Runs the full certification program over the real P1-P9 systems and verifies the directive's
15 criteria, ending with the single evidence-based deployment recommendation. The verdict is
whatever the evidence dictates — no assumptions, no optimism.

    python -m scripts.verify_productization_p10
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

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
    from certification import run_certification, CERTIFIED, CONDITIONALLY_CERTIFIED, NOT_CERTIFIED
    from certification.decision import DecisionEngine
    from certification.scorecards import build_scorecards
    from certification.audits import ProductReadinessAudit, RiskAssessment, GapAnalysis
    from certification.deployment import DeploymentReadinessAudit

    tmp = tempfile.mkdtemp(prefix="nv_p10_verify_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))
    lean = {"benchmark_runs": 2, "reliability_repeats": 2, "reliability_stress": 3,
            "cross_instance": False}
    cert = run_certification(fixtures, validation_kwargs=lean, workspace_dir=str(pathlib.Path(tmp) / "a"))

    # --- 1. certification audit works ---
    try:
        pa = cert["product_audit"]
        check("1. Certification audit works", pa["n_phases"] == 9 and bool(pa["readiness_findings"]),
              f"phases={pa['n_phases']} ready={pa['readiness_state']}")
    except Exception as exc:
        check("1. Certification audit works", False, f"error: {exc}")

    # --- 2. deployment audit works ---
    try:
        da = cert["deployment_audit"]
        check("2. Deployment audit works", len(da["areas"]) == 7,
              f"ready_areas={len(da['ready_areas'])}/7 not_ready={da['not_ready_areas']}")
    except Exception as exc:
        check("2. Deployment audit works", False, f"error: {exc}")

    # --- 3. readiness scoring works ---
    try:
        sc = cert["scorecards"]
        check("3. Readiness scoring works", len(sc["scorecards"]) == 9,
              f"overall_score={sc['overall_score']:.3f} ready={sc['overall_ready']}")
    except Exception as exc:
        check("3. Readiness scoring works", False, f"error: {exc}")

    # --- 4. risk assessment works ---
    try:
        risk = cert["risk"]
        cats = {r["category"] for r in risk["risks"]}
        check("4. Risk assessment works",
              {"data", "model", "deployment", "security", "operational"} <= cats
              and all(r["mitigation_recommendation"] for r in risk["risks"]),
              f"n_risks={risk['n_risks']} critical={len(risk['critical'])} high={len(risk['high'])}")
    except Exception as exc:
        check("4. Risk assessment works", False, f"error: {exc}")

    # --- 5. gap analysis works ---
    try:
        gap = cert["gap"]
        check("5. Gap analysis works",
              bool(gap["exists"]) and bool(gap["partial"]) and bool(gap["missing"]),
              f"exists={len(gap['exists'])} partial={len(gap['partial'])} missing={len(gap['missing'])}")
    except Exception as exc:
        check("5. Gap analysis works", False, f"error: {exc}")

    # --- 6. end-to-end certification works ---
    try:
        e2e = cert["evidence"]["e2e"]
        check("6. End-to-end certification works", e2e["ok"] and e2e["n_checks"] == 10,
              f"checks={e2e['n_checks']} ok={e2e['ok']}")
    except Exception as exc:
        check("6. End-to-end certification works", False, f"error: {exc}")

    # --- 7. decision engine works ---
    try:
        d = cert["decision"]
        check("7. Decision engine works",
              d["verdict"] in {CERTIFIED, CONDITIONALLY_CERTIFIED, NOT_CERTIFIED}
              and {"readiness", "risks", "gaps", "validation", "operations", "deployment"}
              <= set(d["citations"]),
              f"verdict={d['verdict']}")
    except Exception as exc:
        check("7. Decision engine works", False, f"error: {exc}")

    # --- 8. reports generate ---
    try:
        reports = cert["reports"]
        expected = {"deployment_readiness_report", "certification_report", "gap_analysis_report",
                    "risk_report", "executive_summary", "production_qualification_report",
                    "go_no_go_recommendation"}
        check("8. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("8. Reports generate", False, f"error: {exc}")

    # --- 10. existing systems unchanged (certification is one-way, evaluation-only) ---
    try:
        leaks = []
        for pkg in ("preprocessing", "datasets", "ml", "evaluation", "backend", "frontend",
                    "operations", "validation"):
            for path in (REPO / pkg).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    roots = set()
                    if isinstance(node, ast.Import):
                        roots = {a.name.split(".")[0] for a in node.names}
                    elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                        roots = {node.module.split(".")[0]}
                    if "certification" in roots:
                        leaks.append(str(path.relative_to(REPO)))
        check("10. Existing systems unchanged", not leaks,
              "certification is evaluation-only; no domain package imports it")
    except Exception as exc:
        check("10. Existing systems unchanged", False, f"error: {exc}")

    # --- 12. determinism preserved (re-derive decision from the same evidence) ---
    try:
        b = cert["evidence"]
        pa2 = ProductReadinessAudit().run(b)
        da2 = DeploymentReadinessAudit().run(b)
        risk2 = RiskAssessment().run(b)
        gap2 = GapAnalysis().run(b)
        sc2 = build_scorecards(b, product_audit=pa2, deployment_audit=da2, risk=risk2, gap=gap2)
        d2 = DecisionEngine().decide(bundle=b, product_audit=pa2, deployment_audit=da2,
                                     risk=risk2, gap=gap2, scorecards=sc2)
        check("12. Determinism preserved", d2["signature"] == cert["decision"]["signature"],
              "decision is a pure function of the evidence")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. evidence traceability preserved ---
    try:
        traceable = bool(getattr(cert["evidence"]["validation"]["pipeline_result"], "traceable", False))
        compliance_trace = any(c["name"] == "traceability_preserved" and c["passed"]
                               for c in cert["evidence"]["compliance"]["checks"])
        check("13. Evidence traceability preserved", traceable and compliance_trace,
              "prediction chain verifies to the patient")
    except Exception as exc:
        check("13. Evidence traceability preserved", False, f"error: {exc}")

    # --- 14. certification reproducible (a second full run -> same verdict + signature) ---
    try:
        cert2 = run_certification(fixtures, validation_kwargs=lean,
                                  workspace_dir=str(pathlib.Path(tmp) / "b"))
        ok = (cert2["verdict"] == cert["verdict"]
              and cert2["decision"]["signature"] == cert["decision"]["signature"])
        check("14. Certification reproducible", ok,
              f"verdict_stable={cert2['verdict'] == cert['verdict']}")
    except Exception as exc:
        check("14. Certification reproducible", False, f"error: {exc}")

    # --- 15. final deployment recommendation generated ---
    try:
        rec = cert["reports"]["go_no_go_recommendation"]
        check("15. Final deployment recommendation generated",
              bool(rec.get("recommendation")) and bool(rec.get("verdict")),
              f"recommendation={rec.get('recommendation')}")
    except Exception as exc:
        check("15. Final deployment recommendation generated", False, f"error: {exc}")

    # --- 9. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_certification.py"], cwd=str(REPO),
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
    print("\nPRODUCTIZATION P10 — DEPLOYMENT READINESS & PRODUCTION CERTIFICATION")
    print("=" * 72)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 72)
    d = cert["decision"]
    print(f"FINAL VERDICT : {d['verdict']}")
    print(f"RECOMMENDATION: {d['go_no_go']}")
    print(f"SCOPE         : {d['scope']}")
    print(f"CONDITIONS    : {', '.join(d['conditions']) if d['conditions'] else 'none'}")
    print("-" * 72)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
