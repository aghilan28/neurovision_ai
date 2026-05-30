"""Final validation for V4-P1 + V4-P2.

Objectively verifies the directive's 22 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v4_p1_p2
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
    from _v4_helpers import build_v4, goals, active_policies
    from backend.goal_intelligence import (
        GoalCategory, GoalLifecycleState, ancestry, GOAL_CATEGORIES, GOAL_TRANSITIONS,
    )
    from backend.policy_engine import (
        PolicyService, ConstraintType, EvaluationOutcome, PolicyCategory, PolicyRule,
        ConstraintCategory, POLICY_CATEGORIES, PolicyLifecycleState, PolicyGovernanceError,
    )

    fx = build_v4(2)
    tracker = fx.tracker
    gs = fx.goals
    ps = fx.policies
    goal_list = goals(fx)
    policy_list = active_policies(fx)


    # --- goal subsystem (1-7) -----------------------------------------------
    check("1. Goal taxonomy works",
          len(GOAL_CATEGORIES) >= 8
          and ancestry(GoalCategory.WORKFLOW)[-1] == GoalCategory.STRATEGIC
          and len(GOAL_TRANSITIONS) == 8)

    check("2. Goal registry works",
          all(gs.registry.exists(g.goal_id) for g in goal_list)
          and len(gs.registry.list_goals()) == len(goal_list))

    check("3. Goal lifecycle works",
          all(g.state == GoalLifecycleState.ACTIVE for g in goal_list))

    check("4. Goal relationships work",
          all(gs.registry.relationships_for(g.goal_id) for g in goal_list)
          and len(gs.registry.list_relationships()) > 0)

    check("5. Goal governance works",
          all(g.governance.approval_state == "approved" and g.governance.policy_references
              for g in goal_list))

    check("6. Goal lineage works",
          all(tracker.verify_chain(g.lineage_id) for g in goal_list)
          and {"goal", "recommendation", "analytics", "workflow", "event", "case", "patient"}
          <= {r.kind for r in tracker.chain(goal_list[0].lineage_id)})

    check("7. Goal validation works",
          all(gs.validate(g).ok for g in goal_list))

    # --- policy subsystem (8-14) --------------------------------------------
    check("8. Policy taxonomy works",
          len(POLICY_CATEGORIES) == 8 and PolicyCategory.PROHIBITION in POLICY_CATEGORIES)

    # constraint engine: build all six constraint types
    cs_svc = PolicyService(lineage_tracker=tracker)
    built = []
    for ct in ConstraintType:
        c = cs_svc.create_constraint(constraint_type=ct.value,
                                     category=ConstraintCategory.GOVERNANCE, subject_kind="goal",
                                     constraint_key=f"verify-{ct.value}", explanation="x")
        built.append(c.constraint_id.startswith("constraint+") and bool(c.version))
    check("9. Constraint engine works", all(built) and len(built) == 6)

    # evaluation engine: exercise all five outcomes deterministically
    outcomes = _exercise_outcomes(PolicyService, PolicyRule, ConstraintType,
                                  ConstraintCategory, PolicyCategory, EvaluationOutcome, tracker)
    check("10. Policy evaluation engine works",
          outcomes == {o.value for o in EvaluationOutcome},
          f"observed={sorted(outcomes)}")

    check("11. Policy registry works",
          all(ps.registry.exists(p.policy_id) for p in policy_list)
          and len(ps.registry.list_policies()) >= 4)

    # governance: a policy cannot activate without approval
    pg = PolicyService(lineage_tracker=tracker)
    p_un = pg.create_policy(category=PolicyCategory.GOVERNANCE, policy_key="ng", title="T",
                            description="d", subject_kind="goal")
    pg.transition(p_un, PolicyLifecycleState.UNDER_REVIEW)
    denied = False
    try:
        pg.transition(p_un, PolicyLifecycleState.APPROVED, approved=False)
    except PolicyGovernanceError:
        denied = True
    check("12. Policy governance works",
          denied and all(p.approval_state == "approved" for p in policy_list))

    check("13. Policy lineage works",
          all(tracker.verify_chain(p.lineage_id) for p in policy_list)
          and all(tracker.verify_chain(ps.registry.evaluation(eid).lineage_id)
                  for eid in ps.registry.list_evaluations()))

    check("14. Policy validation works",
          all(ps.validate(p).ok for p in policy_list))


    # --- integration + governance + audit + reports (15-18) -----------------
    # 15. goal-policy integration: every governed goal transition produced a policy
    #     evaluation whose lineage reaches the goal it governed.
    eval_ids = ps.registry.list_evaluations()
    integ_ok = bool(eval_ids) and all(
        {"policy_evaluation", "policy", "goal"} <= {r.kind for r in tracker.chain(
            ps.registry.evaluation(eid).lineage_id)} for eid in eval_ids)
    check("15. Goal-policy integration works",
          integ_ok and all(g.governance.policy_references for g in goal_list))

    # 16. governance approvals recorded on both sides
    check("16. Governance approvals work",
          all(any(e.get("decision") in ("permitted", "conditional_approval", "approved")
                  for e in g.governance.approval_history) for g in goal_list)
          and all(p.approval_history for p in policy_list))

    # 17. audit trails immutable + verifiable
    check("17. Audit trails work", gs.audit.verify() and ps.audit.verify())

    # 18. all reports generate correctly
    g_reports = gs.reports(goal_list)
    p_reports = ps.reports(policy_list)
    check("18. All reports generate correctly",
          all(k in g_reports for k in ("goal_summary_report", "goal_registry_report",
                                       "goal_lifecycle_report", "goal_relationship_report",
                                       "goal_governance_report", "goal_audit_report",
                                       "goal_lineage_report"))
          and all(k in p_reports for k in ("policy_summary_report", "policy_registry_report",
                                           "constraint_report", "evaluation_report",
                                           "policy_governance_report", "policy_audit_report",
                                           "policy_lineage_report"))
          and g_reports["goal_audit_report"]["verified"]
          and p_reports["policy_audit_report"]["verified"])

    # --- suite / gates / V3 lineage / boundaries (19-22) --------------------
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_goal_intelligence.py",
         "tests/test_policy_engine.py", "tests/test_v4_p1_p2_e2e.py"],
        cwd=str(REPO), capture_output=True, text=True)
    suite_line = (suite.stdout.strip().splitlines() or [""])[-1]
    check("19. All tests pass", suite.returncode == 0, suite_line)

    # 20. governance gates pass: a fresh build's goals + policies all pass their gates,
    #     and the gates reject malformed artifacts (proven by the suite's negative tests).
    fresh = build_v4(2)
    check("20. Governance gates pass",
          all(fresh.goals.validate(g).ok for g in goals(fresh))
          and all(fresh.policies.validate(p).ok for p in active_policies(fresh)))

    # 21. V3 lineage remains intact (goals/policies only read + extend it)
    v3_ok = (all(tracker.verify_chain(c.lineage_id)
                 for c in fx.base.base.base.cases.values())
             and all(tracker.verify_chain(r.lineage_id)
                     for r in fx.base.recommendation_records["guidance"])
             and fx.base.analytics.audit.verify()
             and fx.base.base.workflows.audit.verify()
             and fx.base.base.graph.audit.verify())
    check("21. Version 3 lineage remains intact", v3_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("22. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # --- report -------------------------------------------------------------
    print("\nV4-P1 + V4-P2 FINAL VALIDATION")
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


def _exercise_outcomes(PolicyService, PolicyRule, ConstraintType, ConstraintCategory,
                       PolicyCategory, EvaluationOutcome, tracker) -> set:
    """Drive one policy per constraint type and collect the evaluation outcomes."""
    svc = PolicyService(lineage_tracker=tracker)
    observed: set = set()

    def active(key, ctype, rules=()):
        c = svc.create_constraint(constraint_type=ctype, category=ConstraintCategory.GOVERNANCE,
                                  subject_kind="goal", constraint_key=key, rules=rules)
        p = svc.create_policy(category=PolicyCategory.GOVERNANCE, policy_key=key, title="T",
                              description="d", subject_kind="goal",
                              constraint_ids=(c.constraint_id,))
        svc.activate(p, authority="gov")
        return p

    sid = "goal+" + "0" * 16
    # PERMITTED — a policy with no triggered (blocking) constraint
    p_ok = svc.create_policy(category=PolicyCategory.GOVERNANCE, policy_key="permit", title="T",
                             description="d", subject_kind="goal")
    svc.activate(p_ok, authority="gov")
    observed.add(svc.evaluate(p_ok, subject_kind="goal", subject_id=sid, request="r",
                              context={}).outcome)
    # DENIED — forbidden constraint always applies
    observed.add(svc.evaluate(active("forbid", ConstraintType.FORBIDDEN.value),
                              subject_kind="goal", subject_id=sid, request="r",
                              context={}).outcome)
    # ESCALATED
    observed.add(svc.evaluate(active("esc", ConstraintType.ESCALATED.value),
                              subject_kind="goal", subject_id=sid, request="r",
                              context={}).outcome)
    # REQUIRES_REVIEW — deferred
    observed.add(svc.evaluate(active("defer", ConstraintType.DEFERRED.value),
                              subject_kind="goal", subject_id=sid, request="r",
                              context={}).outcome)
    # CONDITIONAL_APPROVAL — conditional
    observed.add(svc.evaluate(active("cond", ConstraintType.CONDITIONAL.value),
                              subject_kind="goal", subject_id=sid, request="r",
                              context={}).outcome)
    return observed


if __name__ == "__main__":
    raise SystemExit(main())
