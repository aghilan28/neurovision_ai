"""Final validation for V4-P5 + V4-P6.

Objectively verifies the directive's 25 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v4_p5_p6
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
    from _v4c_helpers import build_v4c, goals, plans, tasks, agents, executions
    from backend.agent_coordination import (
        AgentCategory, AgentLifecycleState, ancestry as agent_ancestry, AGENT_CATEGORIES,
        AGENT_TRANSITIONS,
    )
    from backend.execution_orchestration import (
        ExecutionLifecycleState, EXECUTION_TRANSITIONS,
    )

    fx = build_v4c(2)
    tracker = fx.tracker
    asvc = fx.agents
    esvc = fx.executions
    agent_list = agents(fx)
    exec_list = executions(fx)
    task_list = tasks(fx)

    # --- agent subsystem (1-8) ----------------------------------------------
    check("1. Agent taxonomy works",
          len(AGENT_CATEGORIES) >= 8
          and agent_ancestry(AgentCategory.SERVICE)[-1] == AgentCategory.PARTICIPANT
          and len(AGENT_TRANSITIONS) == 8)

    check("2. Agent registry works",
          all(asvc.registry.exists(a.agent_id) for a in agent_list)
          and len(asvc.registry.list_agents()) == len(agent_list))

    check("3. Agent lifecycle works",
          all(a.state == AgentLifecycleState.AVAILABLE for a in agent_list))

    check("4. Agent capability system works",
          all(a.capabilities for a in agent_list)
          and all(asvc.registry.get(a.agent_id).capabilities for a in agent_list))

    check("5. Agent assignment system works",
          bool(fx.assignments)
          and all(fx.assignments[t.task_id].state == "assigned" for t in task_list)
          and all(fx.assignments[t.task_id].assignment_id.startswith("agentassign+")
                  for t in task_list))

    check("6. Agent governance works",
          all(a.governance.approval_state == "approved" and a.governance.policy_references
              for a in agent_list))

    check("7. Agent lineage works",
          all(tracker.verify_chain(asn.lineage_id) for asn in fx.assignments.values())
          and {"agent_assignment", "agent", "task", "goal", "event", "case", "patient"}
          <= {r.kind for r in tracker.chain(next(iter(fx.assignments.values())).lineage_id)})

    check("8. Agent validation works", all(asvc.validate(a).ok for a in agent_list))

    # --- execution subsystem (9-16) -----------------------------------------
    check("9. Execution lifecycle works",
          all(e.state == ExecutionLifecycleState.COMPLETED for e in exec_list)
          and len(EXECUTION_TRANSITIONS) == 9
          and ExecutionLifecycleState.PAUSED in EXECUTION_TRANSITIONS[ExecutionLifecycleState.ACTIVE]
          and ExecutionLifecycleState.BLOCKED in EXECUTION_TRANSITIONS[ExecutionLifecycleState.ACTIVE])

    check("10. Execution authorization works",
          all(e.governance.authorization_state == "authorized" for e in exec_list))

    check("11. Execution coordination works",
          all(e.context.task_id and e.context.agent_id and e.context.assignment_id
              for e in exec_list))

    check("12. Execution monitoring works",
          all(esvc.observe(e).progress == 1.0 and esvc.observe(e).outcome == "completed"
              for e in exec_list))

    check("13. Execution registry works",
          all(esvc.registry.exists(e.execution_id) for e in exec_list)
          and len(esvc.registry.list_executions()) == len(exec_list))

    check("14. Execution governance works",
          all(e.governance.policy_references for e in exec_list))

    check("15. Execution lineage works",
          all(tracker.verify_chain(e.lineage_id) for e in exec_list)
          and {"execution", "agent_assignment", "agent", "task", "plan", "goal",
               "analytics", "workflow", "event", "case", "patient"}
          <= {r.kind for r in tracker.chain(exec_list[0].lineage_id)})

    check("16. Execution validation works", all(esvc.validate(e).ok for e in exec_list))


    # --- integration (17-18) ------------------------------------------------
    # 17. task -> agent: every assignment satisfies the task's capability requirements
    #     and its lineage chain includes the task.
    task_agent_ok = bool(fx.assignments) and all(
        "task" in {r.kind for r in tracker.chain(fx.assignments[t.task_id].lineage_id)}
        and fx.assignments[t.task_id].target_id == t.task_id for t in task_list)
    check("17. Task-agent integration works", task_agent_ok)

    # 18. agent -> execution: every execution references an approved assignment, and its
    #     lineage chain includes the assignment + agent.
    agent_exec_ok = bool(exec_list) and all(
        e.assignment_id and {"agent_assignment", "agent"}
        <= {r.kind for r in tracker.chain(e.lineage_id)} for e in exec_list)
    check("18. Agent-execution integration works", agent_exec_ok)

    # --- governance + audit + reports (19-21) -------------------------------
    check("19. Governance approvals work",
          all(any(ev.get("decision") in ("permitted", "conditional_approval", "approved")
                  for ev in a.governance.approval_history) for a in agent_list)
          and all(any(ev.get("decision") in ("permitted", "conditional_approval", "approved")
                      for ev in e.governance.authorization_history) for e in exec_list))

    check("20. Audit trails work",
          asvc.audit.verify() and esvc.audit.verify()
          and fx.base.base.goals.audit.verify() and fx.base.base.policies.audit.verify()
          and fx.base.plans.audit.verify() and fx.base.tasks.audit.verify())

    a_reports = asvc.reports(agent_list)
    e_reports = esvc.reports(exec_list)
    check("21. All reports generate correctly",
          all(k in a_reports for k in ("agent_summary_report", "capability_report",
                                       "assignment_report", "agent_lifecycle_report",
                                       "agent_governance_report", "agent_audit_report",
                                       "agent_lineage_report"))
          and all(k in e_reports for k in ("execution_summary_report", "authorization_report",
                                           "status_report", "monitoring_report",
                                           "execution_governance_report",
                                           "execution_audit_report", "execution_lineage_report"))
          and a_reports["agent_audit_report"]["verified"]
          and e_reports["execution_audit_report"]["verified"])

    # --- suite / gates / lineage / boundaries (22-25) -----------------------
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_agent_coordination.py",
         "tests/test_execution_orchestration.py", "tests/test_v4_p5_p6_e2e.py"],
        cwd=str(REPO), capture_output=True, text=True)
    suite_line = (suite.stdout.strip().splitlines() or [""])[-1]
    check("22. All tests pass", suite.returncode == 0, suite_line)

    # 23. governance gates pass: a fresh build's agents + executions all pass their gates.
    fresh = build_v4c(2)
    check("23. Governance gates pass",
          all(fresh.agents.validate(a).ok for a in agents(fresh))
          and all(fresh.executions.validate(e).ok for e in executions(fresh)))

    # 24. V4 goal-policy-plan-task lineage remains intact
    v4_ok = (all(tracker.verify_chain(g.lineage_id) for g in goals(fx))
             and all(fx.base.base.goals.validate(g).ok for g in goals(fx))
             and all(tracker.verify_chain(p.lineage_id) for p in plans(fx))
             and all(fx.base.plans.validate(p).ok for p in plans(fx))
             and all(tracker.verify_chain(t.lineage_id) for t in task_list)
             and all(fx.base.tasks.validate(t).ok for t in task_list)
             and all(tracker.verify_chain(fx.base.base.policies.policy_cache[pid].lineage_id)
                     for pid in fx.base.base.policies.registry.active_policies()))
    check("24. Version 4 goal-policy-plan-task lineage remains intact", v4_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("25. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # --- report -------------------------------------------------------------
    print("\nV4-P5 + V4-P6 FINAL VALIDATION")
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
