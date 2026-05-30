"""Final validation for V4-P7 + V4-P8.

Objectively verifies the directive's 27 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v4_p7_p8
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO / "tests"))
    from _v4d_helpers import build_v4d, build_aow_snapshot
    from _v4c_helpers import goals, plans, tasks, agents, executions
    from backend.governance_intelligence import (
        GovernanceIntelligenceGate, GovernanceIntelligenceRecord, GovernedObservation,
        GovernedKind, ViolationType, RISK_DIMENSIONS,
        detect_violations, build_escalations, monitoring_summary,
    )
    from frontend.autonomous_operations_workstation import (
        build_from_snapshot, WorkstationState, validate_state, build_controls,
        controls_summary,
    )

    fx = build_v4d(2)
    tracker = fx.tracker
    gi = fx.governance
    rec = fx.intelligence
    snap = build_aow_snapshot(fx)
    view = build_from_snapshot(snap).to_dict()

    def area(area_id):
        return next(a for a in view["areas"] if a["id"] == area_id)

    # --- governance intelligence (1-8) --------------------------------------
    check("1. Approval intelligence works",
          len(rec.approvals) == rec.n_observed and rec.n_observed > 0
          and all(a.latency_steps >= 0 for a in rec.approvals)
          and any(a.approved for a in rec.approvals))

    # violation intelligence: clean platform yields none; the detector flags a bad state.
    bad = GovernedObservation(
        kind=GovernedKind.EXECUTION, entity_id="execution+deadbeefdeadbeef",
        approval_state="denied", decision="denied", authority=None, history=(),
        escalation_required=False, escalated=False, policy_references=(), state="active",
        lineage_id="lineage+0000000000000000", live=True)
    detected = {v.violation_type for v in detect_violations([bad])}
    check("2. Violation intelligence works",
          rec.violations == () and ViolationType.LIFECYCLE in detected
          and ViolationType.AUTHORIZATION in detected)

    esc_obs = GovernedObservation(
        kind=GovernedKind.AGENT, entity_id="agent+1111111111111111", approval_state="escalated",
        decision="escalated", authority="gov", history=({"decision": "escalated"},),
        escalation_required=True, escalated=True, policy_references=("p1",),
        state="under_review", lineage_id="lineage+1111111111111111", live=False)
    esc = build_escalations([esc_obs])
    check("3. Escalation intelligence works",
          len(esc) == 1 and esc[0].requested and esc[0].delay_steps >= 0)

    check("4. Governance risk engine works",
          bool(rec.risks) and all(0.0 <= r.score <= 1.0 for r in rec.risks)
          and all(r.dimension in RISK_DIMENSIONS and r.factors and r.explanation
                  for r in rec.risks))

    metric_names = {m.name for m in rec.metrics}
    check("5. Governance analytics works",
          {"governance_health", "approval_health", "overall_risk"} <= metric_names
          and 0.0 <= rec.health_score <= 1.0)

    check("6. Governance registry works",
          gi.registry.exists(rec.intelligence_id)
          and len(gi.registry.list_approvals()) == len(rec.approvals)
          and len(gi.registry.list_risks()) == len(rec.risks))

    chain_kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
    check("7. Governance lineage works",
          tracker.verify_chain(rec.lineage_id)
          and {"governance_intelligence", "goal", "policy", "plan", "task", "agent",
               "execution", "patient"} <= chain_kinds)

    check("8. Governance validation works", gi.validate(rec).ok)

    # --- workstation workspaces (9-21) --------------------------------------
    def workspace_ok(area_id, expect_table_rows=True):
        a = area(area_id)
        if not a["pages"]:
            return False
        page = a["pages"][0]
        if not expect_table_rows:
            return bool(page["sections"])
        tables = [s for s in page["sections"] if s["kind"] == "table"]
        return bool(tables) and any(t["data"]["rows"] for t in tables)

    check("9. Goal workspace works", workspace_ok("goals"))
    check("10. Policy workspace works", workspace_ok("policies"))
    check("11. Plan workspace works", workspace_ok("plans"))
    check("12. Task workspace works", workspace_ok("tasks"))
    check("13. Agent workspace works",
          workspace_ok("agents")
          and any(c["action"] == "suspend_agent"
                  for p in area("agents")["pages"] for c in p["controls"]))
    exec_actions = {c["action"] for p in area("executions")["pages"] for c in p["controls"]}
    check("14. Execution workspace works",
          workspace_ok("executions")
          and {"pause_execution", "terminate_execution"} <= exec_actions)

    gov_pages = {p["id"] for p in area("governance")["pages"]}
    check("15. Governance workspace works",
          {"governance-health", "governance-approvals", "governance-violations",
           "governance-escalations", "governance-risk"} <= gov_pages)

    audit_page = area("audit")["pages"][0]
    audit_kv = next(s for s in audit_page["sections"] if s["kind"] == "kv")
    check("16. Audit browser works", audit_kv["data"]["all_verified"] is True)

    lineage_page = area("lineage")["pages"][0]
    spine_badges = next(s for s in lineage_page["sections"] if s["kind"] == "badges")
    spine = {b["label"]: b["value"] for b in spine_badges["data"]["badges"]}
    check("17. Lineage explorer works",
          all(spine.get(k) for k in ("patient", "goal", "policy", "plan", "task", "agent",
                                     "execution", "governance_intelligence")))

    controls = build_controls(WorkstationState.from_snapshot(snap))
    csummary = controls_summary(controls)
    check("18. Intervention controls work",
          bool(controls) and csummary["all_governed"]
          and {"suspend_agent", "pause_execution", "terminate_execution", "escalate_approval",
               "request_review"} <= set(csummary["by_action"]))

    report_table = next(s for s in area("reports")["pages"][0]["sections"]
                        if s["kind"] == "table")
    report_subsystems = {row[0] for row in report_table["data"]["rows"]}
    check("19. Report center works",
          {"goals", "policies", "plans", "tasks", "agents", "executions", "governance"}
          <= report_subsystems)

    state = WorkstationState.from_snapshot(snap).default_context()
    ctx = state.context_snapshot()
    check("20. State management works",
          bool(state.record("goals", ctx["current_goal"]))
          and bool(state.record("executions", ctx["current_execution"]))
          and ctx["current_governance"] == rec.intelligence_id)

    wval = validate_state(state).to_dict()
    check("21. Workstation validation works", wval["ok"] and wval["n_checks"] == 6)

    # --- governance + audit + integrity (22-27) -----------------------------
    check("22. Governance approvals work",
          all(a.approved for a in rec.approvals
              if a.entity_kind in (GovernedKind.GOAL, GovernedKind.PLAN, GovernedKind.TASK,
                                   GovernedKind.AGENT, GovernedKind.EXECUTION))
          and len(area("governance")["pages"]) >= 5)

    check("23. Audit trails work",
          gi.audit.verify() and fx.base.agents.audit.verify()
          and fx.base.executions.audit.verify()
          and fx.base.base.base.goals.audit.verify()
          and fx.base.base.base.policies.audit.verify()
          and fx.base.base.plans.audit.verify() and fx.base.base.tasks.audit.verify())

    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_governance_intelligence.py",
         "tests/test_autonomous_operations_workstation.py", "tests/test_v4_p7_p8_e2e.py"],
        cwd=str(REPO), capture_output=True, text=True)
    suite_line = (suite.stdout.strip().splitlines() or [""])[-1]
    check("24. All tests pass", suite.returncode == 0, suite_line)

    # 25. governance gates pass: fresh build admitted + monitoring engine works.
    fresh = build_v4d(2)
    blocked = GovernedObservation(
        kind=GovernedKind.EXECUTION, entity_id="execution+2222222222222222",
        approval_state="authorized", decision="permitted", authority="gov", history=(),
        escalation_required=False, escalated=False, policy_references=("p1",), state="blocked",
        lineage_id="lineage+2222222222222222", live=True)
    gate = GovernanceIntelligenceGate()
    bad_record = GovernanceIntelligenceRecord(intelligence_id="govintel+deadbeefdeadbeef",
                                              scope="operational", health_score=2.0)
    check("25. Governance gates pass",
          fresh.governance.validate(fresh.intelligence).ok
          and not gate.evaluate(record=bad_record, parents=(), requires_lineage=False).ok
          and monitoring_summary([blocked])["n_executions_requiring_intervention"] == 1)

    # 26. V4 goal-policy-plan-task-agent-execution lineage remains intact
    base = fx.base
    v4_ok = (all(tracker.verify_chain(g.lineage_id) and base.base.base.goals.validate(g).ok
                 for g in goals(base))
             and all(tracker.verify_chain(p.lineage_id) and base.base.plans.validate(p).ok
                     for p in plans(base))
             and all(tracker.verify_chain(t.lineage_id) and base.base.tasks.validate(t).ok
                     for t in tasks(base))
             and all(tracker.verify_chain(a.lineage_id) and base.agents.validate(a).ok
                     for a in agents(base))
             and all(tracker.verify_chain(e.lineage_id) and base.executions.validate(e).ok
                     for e in executions(base)))
    check("26. Version 4 lineage remains intact", v4_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("27. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # --- report -------------------------------------------------------------
    print("\nV4-P7 + V4-P8 FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)
    print("=" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
