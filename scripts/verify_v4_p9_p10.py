"""Final validation for V4-P9 + V4-P10 (and the Version 4 certification outcome).

Objectively verifies the directive's 25 final-validation criteria, prints a measurable
readiness scorecard (V4-P10), and emits the objective Version 4 certification outcome.
Exits non-zero if any criterion fails or the version is not certifiable.

    python -m scripts.verify_v4_p9_p10
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CERT_DIR = REPO / "docs" / "certification" / "v4"
CERT_DOCS = [
    "V4_CERTIFICATION_STANDARD.md", "V4_READINESS_ASSESSMENT.md", "V4_AUDIT_FRAMEWORK.md",
    "V4_RISK_REVIEW.md", "V4_GAP_ANALYSIS.md", "V4_EXIT_CRITERIA.md",
    "V4_COMPLETION_REPORT.md", "V5_READINESS_GATE.md",
]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO / "tests"))
    from _v4e_helpers import build_v4e, baseline
    from _v4c_helpers import goals, plans, tasks, agents, executions
    from backend.simulation_scenario import (
        SimulationGate, SCENARIO_TYPES, SIM_DIMENSIONS,
        FORECAST_TYPES, SIM_RISK_DIMENSIONS,
    )
    from backend.simulation_scenario.models.domain import SimulationOutcome
    from dataclasses import replace

    fx = build_v4e(2)
    tracker = fx.tracker
    svc = fx.simulation
    base = fx.base.base                      # V4cFixture

    # baseline + a what-if scenario for comparison
    sc_a, sim_a = baseline(svc, "execution")
    aid = agents(base)[0].agent_id
    sc_b = svc.create_scenario(scenario_type="execution", name="exclude-agent",
                               assumptions={"exclude_agents": [aid]})
    sim_b = svc.simulate(sc_b)
    comparison = svc.compare([(sc_a, sim_a), (sc_b, sim_b)])

    # --- simulation layer (1-12) --------------------------------------------
    scenario_ids = [svc.create_scenario(scenario_type=t, name=f"{t}-s").scenario_id
                    for t in SCENARIO_TYPES]
    check("1. Scenario engine works",
          len(scenario_ids) == len(SCENARIO_TYPES) and all(s.startswith("scenario+")
                                                           for s in scenario_ids))
    check("2. Simulation engine works",
          set(SIM_DIMENSIONS) <= {o.dimension for o in sim_a.result.outcomes}
          and 0.0 <= sim_a.result.readiness_score <= 1.0)
    check("3. Forecast layer works",
          set(FORECAST_TYPES) <= {f.forecast_type for f in sim_a.result.forecasts}
          and all(f.factors and f.explanation and 0.0 <= f.confidence <= 1.0
                  for f in sim_a.result.forecasts))
    check("4. Comparison engine works",
          comparison.recommended_scenario_id in comparison.scenario_ids
          and bool(comparison.tradeoffs) and bool(comparison.governance_impact))
    check("5. Simulation risk engine works",
          SIM_RISK_DIMENSIONS <= {r.dimension for r in sim_a.result.risks}
          and all(0.0 <= r.score <= 1.0 and r.factors for r in sim_a.result.risks))
    check("6. Simulation registry works",
          svc.registry.exists(sc_a.scenario_id) and svc.registry.exists(sim_a.simulation_id)
          and bool(svc.registry.list_forecasts()) and bool(svc.registry.list_risks()))
    chain_kinds = {r.kind for r in tracker.chain(sim_a.lineage_id)}
    check("7. Simulation lineage works",
          tracker.verify_chain(sim_a.lineage_id)
          and {"patient", "goal", "policy", "plan", "task", "agent", "execution",
               "governance_intelligence", "scenario", "simulation"} <= chain_kinds)
    check("8. Simulation validation works",
          svc.validate(simulation=sim_a, scenario=sc_a, comparison=comparison).ok)

    reports = svc.reports(scenario=sc_a, simulation=sim_a, comparison=comparison)
    check("9. Scenario reports work", "scenario_report" in reports
          and reports["scenario_report"]["scenario_id"] == sc_a.scenario_id)
    check("10. Simulation reports work", "simulation_report" in reports
          and reports["simulation_report"]["readiness_status"] in ("ready", "degraded", "blocked"))
    check("11. Forecast reports work", "forecast_report" in reports
          and reports["forecast_report"]["summary"]["n_forecasts"] == len(FORECAST_TYPES))
    check("12. Comparison reports work", "comparison_report" in reports
          and reports["comparison_report"]["recommended_scenario_id"]
          == comparison.recommended_scenario_id)

    # --- certification framework (13-19) ------------------------------------
    docs_present = {d: (CERT_DIR / d).is_file() and len((CERT_DIR / d).read_text()) > 400
                    for d in CERT_DOCS}
    check("13. Certification framework complete",
          all(docs_present.values()) and (CERT_DIR / "V4_CERTIFICATION_STANDARD.md").is_file(),
          f"docs={sum(docs_present.values())}/{len(CERT_DOCS)}")

    # measurable readiness scorecard (also satisfies criterion 14)
    scorecard = _readiness_scorecard(REPO)
    check("14. Readiness assessment complete",
          (CERT_DIR / "V4_READINESS_ASSESSMENT.md").is_file()
          and all(v == 1.0 for v in scorecard.values()),
          "all dimensions 1.0" if all(v == 1.0 for v in scorecard.values())
          else f"failing: {[k for k, v in scorecard.items() if v < 1.0]}")

    audit_text = (CERT_DIR / "V4_AUDIT_FRAMEWORK.md").read_text()
    check("15. Audit framework complete",
          all(k in audit_text for k in ("Audit procedures", "Severity model",
                                        "Remediation model", "Closure model")))
    risk_text = (CERT_DIR / "V4_RISK_REVIEW.md").read_text()
    check("16. Risk review complete",
          all(k in risk_text for k in ("Architecture risks", "Simulation risks",
                                       "Future risks", "Unknown risks")))
    gap_text = (CERT_DIR / "V4_GAP_ANALYSIS.md").read_text()
    check("17. Gap analysis complete",
          "Severity classification" in gap_text and "Remediation framework" in gap_text)
    exit_text = (CERT_DIR / "V4_EXIT_CRITERIA.md").read_text()
    check("18. Exit criteria validated", "EC-1" in exit_text and "EC-18" in exit_text)
    gate_text = (CERT_DIR / "V5_READINESS_GATE.md").read_text()
    check("19. V5 readiness gate defined",
          "Forbidden shortcuts" in gate_text and "G1" in gate_text and "DENIED" in gate_text)

    # --- governance/audit/tests/lineage/boundary (20-24) --------------------
    gate = SimulationGate()
    bad_outcomes = (SimulationOutcome(dimension="execution_structures", status="executed",
                                      score=1.0, detail="x", metrics={}),)
    bad_sim = replace(sim_a, result=replace(sim_a.result, outcomes=bad_outcomes))
    good_ok = gate.evaluate_simulation(simulation=sim_a, parents=(sc_a.lineage_id,)).ok
    bad_rejected = not gate.evaluate_simulation(simulation=bad_sim,
                                                parents=(sc_a.lineage_id,)).ok
    check("20. Governance gates pass", good_ok and bad_rejected)

    check("21. Audit trails pass",
          svc.audit.verify() and fx.base.governance.audit.verify()
          and base.agents.audit.verify() and base.executions.audit.verify()
          and base.base.base.goals.audit.verify() and base.base.base.policies.audit.verify()
          and base.base.plans.audit.verify() and base.base.tasks.audit.verify())

    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_simulation_scenario.py",
         "tests/test_v4_p9_p10_e2e.py"], cwd=str(REPO), capture_output=True, text=True)
    check("22. All tests pass", suite.returncode == 0,
          (suite.stdout.strip().splitlines() or [""])[-1])

    v4_ok = (all(tracker.verify_chain(g.lineage_id) and base.base.base.goals.validate(g).ok
                 for g in goals(base))
             and all(tracker.verify_chain(p.lineage_id) and base.base.plans.validate(p).ok
                     for p in plans(base))
             and all(tracker.verify_chain(t.lineage_id) and base.base.tasks.validate(t).ok
                     for t in tasks(base))
             and all(tracker.verify_chain(a.lineage_id) and base.agents.validate(a).ok
                     for a in agents(base))
             and all(tracker.verify_chain(e.lineage_id) and base.executions.validate(e).ok
                     for e in executions(base))
             and fx.base.governance.validate(fx.base.intelligence).ok)
    check("23. Version 4 lineage remains intact", v4_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("24. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # --- certification outcome (25) -----------------------------------------
    sim_criteria_ok = all(ok for name, ok, _ in checks
                          if name[0].isdigit() and int(name.split(".")[0]) <= 24)
    readiness_ok = all(v == 1.0 for v in scorecard.values())
    certified = sim_criteria_ok and readiness_ok
    check("25. Certification outcome objectively justified", certified,
          "all 1-24 PASS and readiness scorecard all 1.0" if certified
          else "unmet criteria or readiness gap")

    # --- report -------------------------------------------------------------
    print("\nV4-P9 + V4-P10 FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)

    print("-" * 64)
    print("V4 READINESS SCORECARD (V4-P10)")
    for dim, score in scorecard.items():
        print(f"  [{'PASS' if score == 1.0 else 'FAIL'}] {dim:<24} {score:.2f}")

    print("=" * 64)
    print("CRITERIA RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    print("VERSION 4 CERTIFICATION OUTCOME:",
          "CERTIFIED" if (all_ok and readiness_ok) else "NOT CERTIFIED")
    return 0 if (all_ok and readiness_ok) else 1


def _verify_script_ok(repo: pathlib.Path, module: str) -> bool:
    res = subprocess.run([sys.executable, "-m", f"scripts.{module}"], cwd=str(repo),
                         capture_output=True, text=True)
    return res.returncode == 0 and "ALL CRITERIA PASS" in res.stdout


def _readiness_scorecard(repo: pathlib.Path) -> dict:
    """Measurable per-dimension readiness (1.0 == every required check passes)."""
    p12 = _verify_script_ok(repo, "verify_v4_p1_p2")
    p34 = _verify_script_ok(repo, "verify_v4_p3_p4")
    p56 = _verify_script_ok(repo, "verify_v4_p5_p6")
    p78 = _verify_script_ok(repo, "verify_v4_p7_p8")

    suite = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(repo),
                           capture_output=True, text=True)
    suite_ok = suite.returncode == 0
    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(repo), capture_output=True, text=True)
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check",
                           "backend/simulation_scenario", "backend/governance_intelligence",
                           "frontend/autonomous_operations_workstation"],
                          cwd=str(repo), capture_output=True, text=True)
    repo_ok = suite_ok and bnd.returncode == 0 and ruff.returncode == 0

    sim_tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_simulation_scenario.py",
         "tests/test_v4_p9_p10_e2e.py"], cwd=str(repo), capture_output=True, text=True)
    sim_ok = sim_tests.returncode == 0

    return {
        "Goal Readiness": 1.0 if p12 else 0.0,
        "Policy Readiness": 1.0 if p12 else 0.0,
        "Planning Readiness": 1.0 if p34 else 0.0,
        "Task Readiness": 1.0 if p34 else 0.0,
        "Agent Readiness": 1.0 if p56 else 0.0,
        "Execution Readiness": 1.0 if p56 else 0.0,
        "Governance Readiness": 1.0 if p78 else 0.0,
        "Workstation Readiness": 1.0 if p78 else 0.0,
        "Simulation Readiness": 1.0 if sim_ok else 0.0,
        "Repository Readiness": 1.0 if repo_ok else 0.0,
        "Version Readiness": 1.0 if (suite_ok and sim_ok) else 0.0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
