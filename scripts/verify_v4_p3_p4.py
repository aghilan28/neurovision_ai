"""Final validation for V4-P3 + V4-P4.

Objectively verifies the directive's 23 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v4_p3_p4
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
    from _v4b_helpers import build_v4b, goals, plans, tasks
    from backend.planning_foundation import (
        PlanCategory, PlanLifecycleState, ancestry as plan_ancestry, has_cycle as plan_has_cycle,
        PLAN_CATEGORIES, PLAN_TRANSITIONS,
    )
    from backend.task_intelligence import (
        TaskCategory, TaskLifecycleState, ancestry as task_ancestry, has_cycle as task_has_cycle,
        TASK_CATEGORIES, TASK_TRANSITIONS,
    )

    fx = build_v4b(2)
    tracker = fx.tracker
    plan_svc = fx.plans
    task_svc = fx.tasks
    plan_list = plans(fx)
    task_list = tasks(fx)
    goal_list = goals(fx)

    def _deps(registry):
        return [registry.dependency(d) for d in registry.list_dependencies()]

    # --- plan subsystem (1-7) -----------------------------------------------
    check("1. Plan taxonomy works",
          len(PLAN_CATEGORIES) >= 8
          and plan_ancestry(PlanCategory.WORKFLOW)[-1] == PlanCategory.STRATEGIC
          and len(PLAN_TRANSITIONS) == 8)

    check("2. Plan registry works",
          all(plan_svc.registry.exists(p.plan_id) for p in plan_list)
          and len(plan_svc.registry.list_plans()) == len(plan_list))

    check("3. Plan lifecycle works",
          all(p.state == PlanLifecycleState.READY for p in plan_list))

    check("4. Plan dependencies work",
          all(plan_svc.registry.dependencies_for(p.plan_id) for p in plan_list)
          and not plan_has_cycle(_deps(plan_svc.registry)))

    check("5. Plan governance works",
          all(p.governance.approval_state == "approved" and p.governance.policy_references
              for p in plan_list))

    check("6. Plan lineage works",
          all(tracker.verify_chain(p.lineage_id) for p in plan_list)
          and {"plan", "goal", "analytics", "workflow", "event", "case", "patient"}
          <= {r.kind for r in tracker.chain(plan_list[0].lineage_id)})

    check("7. Plan validation works", all(plan_svc.validate(p).ok for p in plan_list))

    # --- task subsystem (8-14) ----------------------------------------------
    check("8. Task taxonomy works",
          len(TASK_CATEGORIES) >= 8
          and task_ancestry(TaskCategory.VALIDATION)[-1] == TaskCategory.OPERATIONAL
          and len(TASK_TRANSITIONS) == 8)

    check("9. Task registry works",
          all(task_svc.registry.exists(t.task_id) for t in task_list)
          and len(task_svc.registry.list_tasks()) == len(task_list))

    check("10. Task lifecycle works",
          all(t.state == TaskLifecycleState.READY for t in task_list)
          and TaskLifecycleState.BLOCKED in TASK_TRANSITIONS[TaskLifecycleState.READY])

    check("11. Task dependencies work",
          all(task_svc.registry.dependencies_for(t.task_id) for t in task_list)
          and not task_has_cycle(_deps(task_svc.registry)))

    check("12. Task governance works",
          all(t.governance.approval_state == "approved" and t.governance.policy_references
              for t in task_list))

    check("13. Task lineage works",
          all(tracker.verify_chain(t.lineage_id) for t in task_list)
          and {"task", "plan", "goal", "analytics", "workflow", "event", "case", "patient"}
          <= {r.kind for r in tracker.chain(task_list[0].lineage_id)})

    check("14. Task validation works", all(task_svc.validate(t).ok for t in task_list))


    # --- integration (15-16) ------------------------------------------------
    # 15. goal -> plan: every plan derives from one of the (approved/active) goals,
    #     and its lineage chain includes that goal.
    goal_ids = {g.goal_id for g in goal_list}
    goal_plan_ok = bool(plan_list) and all(
        p.source_goal_id in goal_ids
        and "goal" in {r.kind for r in tracker.chain(p.lineage_id)} for p in plan_list)
    check("15. Goal-plan integration works", goal_plan_ok)

    # 16. plan -> task: every task derives from a READY plan, and its lineage chain
    #     includes that plan.
    plan_ids = {p.plan_id for p in plan_list}
    plan_task_ok = bool(task_list) and all(
        t.source_plan_id in plan_ids
        and "plan" in {r.kind for r in tracker.chain(t.lineage_id)} for t in task_list)
    check("16. Plan-task integration works", plan_task_ok)

    # --- governance + audit + reports (17-19) -------------------------------
    # 17. governance approvals recorded on both plans and tasks
    check("17. Governance approvals work",
          all(any(e.get("decision") in ("permitted", "conditional_approval", "approved")
                  for e in p.governance.approval_history) for p in plan_list)
          and all(any(e.get("decision") in ("permitted", "conditional_approval", "approved")
                      for e in t.governance.approval_history) for t in task_list))

    # 18. audit trails immutable + verifiable (both subsystems + the goal/policy base)
    check("18. Audit trails work",
          plan_svc.audit.verify() and task_svc.audit.verify()
          and fx.base.goals.audit.verify() and fx.base.policies.audit.verify())

    # 19. all reports generate correctly
    p_reports = plan_svc.reports(plan_list)
    t_reports = task_svc.reports(task_list)
    check("19. All reports generate correctly",
          all(k in p_reports for k in ("plan_summary_report", "plan_registry_report",
                                       "plan_lifecycle_report", "plan_dependency_report",
                                       "plan_governance_report", "plan_audit_report",
                                       "plan_lineage_report"))
          and all(k in t_reports for k in ("task_summary_report", "task_registry_report",
                                           "task_lifecycle_report", "task_dependency_report",
                                           "task_governance_report", "task_audit_report",
                                           "task_lineage_report"))
          and p_reports["plan_audit_report"]["verified"]
          and t_reports["task_audit_report"]["verified"])

    # --- suite / gates / lineage / boundaries (20-23) -----------------------
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_planning_foundation.py",
         "tests/test_task_intelligence.py", "tests/test_v4_p3_p4_e2e.py"],
        cwd=str(REPO), capture_output=True, text=True)
    suite_line = (suite.stdout.strip().splitlines() or [""])[-1]
    check("20. All tests pass", suite.returncode == 0, suite_line)

    # 21. governance gates pass: a fresh build's plans + tasks all pass their gates.
    fresh = build_v4b(2)
    check("21. Governance gates pass",
          all(fresh.plans.validate(p).ok for p in plans(fresh))
          and all(fresh.tasks.validate(t).ok for t in tasks(fresh)))

    # 22. V4 goal-policy lineage remains intact (plans/tasks only read + extend it)
    v4_ok = (all(tracker.verify_chain(g.lineage_id) for g in goal_list)
             and all(fx.base.goals.validate(g).ok for g in goal_list)
             and all(tracker.verify_chain(fx.base.policies.policy_cache[pid].lineage_id)
                     for pid in fx.base.policies.registry.active_policies()))
    check("22. Version 4 goal-policy lineage remains intact", v4_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("23. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # --- report -------------------------------------------------------------
    print("\nV4-P3 + V4-P4 FINAL VALIDATION")
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
