"""End-to-end V4-P3 + V4-P4 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event ->
    Timeline -> Workflow -> Graph -> Analytics -> Recommendations -> Goal ->
    Policy -> Constraint -> Plan -> Task -> Governance

over the real V2/V3/V4 artifacts on one shared lineage tracker, and that all
cross-version invariants hold (V4 goal-policy lineage intact, determinism, audit
immutability, plans/tasks never execute, every ready plan/task policy-governed).
"""

from __future__ import annotations

from _v4b_helpers import build_v4b, goals, plans, tasks
from backend.planning_foundation import PlanLifecycleState


def test_full_chain_executes_with_traceability():
    fx = build_v4b(2)
    tracker = fx.tracker

    # --- plans reach READY, validate, and trace to the patient --------------
    ps = plans(fx)
    assert ps and all(p.is_ready for p in ps)
    for p in ps:
        assert fx.plans.validate(p).ok
        kinds = {r.kind for r in tracker.chain(p.lineage_id)}
        for k in ("plan", "goal", "recommendation", "analytics", "workflow", "event",
                  "case", "patient"):
            assert k in kinds, f"missing {k} in plan lineage"
        assert tracker.verify_chain(p.lineage_id)

    # --- tasks reach READY, validate, and trace to the patient --------------
    ts = tasks(fx)
    assert ts and all(t.is_ready for t in ts)
    for t in ts:
        assert fx.tasks.validate(t).ok
        kinds = {r.kind for r in tracker.chain(t.lineage_id)}
        for k in ("task", "plan", "goal", "analytics", "workflow", "event", "case", "patient"):
            assert k in kinds, f"missing {k} in task lineage"
        assert tracker.verify_chain(t.lineage_id)
        # the task is policy-governed (its readiness produced a policy decision)
        assert t.governance.policy_references

    # --- audit trails immutable + intact (every subsystem) ------------------
    assert fx.plans.audit.verify() and fx.tasks.audit.verify()
    assert fx.base.goals.audit.verify() and fx.base.policies.audit.verify()

    # --- policy evaluations exist and themselves trace to the patient -------
    eval_ids = fx.base.policies.registry.list_evaluations()
    assert eval_ids
    # plan/task readiness evaluations parent the plan/task node -> trace to patient
    plan_task_evals = [fx.base.policies.registry.evaluation(eid) for eid in eval_ids
                       if fx.base.policies.registry.evaluation(eid).subject_kind in ("plan", "task")]
    assert plan_task_evals
    for ev in plan_task_evals:
        assert tracker.verify_chain(ev.lineage_id)

    # --- V4 goal-policy lineage remains intact ------------------------------
    for g in goals(fx):
        assert tracker.verify_chain(g.lineage_id) and fx.base.goals.validate(g).ok
    for pid in fx.base.policies.registry.active_policies():
        pol = fx.base.policies.policy_cache[pid]
        assert tracker.verify_chain(pol.lineage_id) and fx.base.policies.validate(pol).ok


def test_every_ready_plan_and_task_is_policy_governed():
    fx = build_v4b(2)
    for p in plans(fx):
        assert p.governance.policy_references and p.governance.approval_state == "approved"
    for t in tasks(fx):
        assert t.governance.policy_references and t.governance.approval_state == "approved"


def test_plans_and_tasks_carry_no_execution():
    """Plans are intent structures; tasks describe work — neither executes."""
    fx = build_v4b(2)
    for p in plans(fx):
        d = p.to_dict()
        for forbidden in ("execute", "run", "agent", "job", "process", "autonomous"):
            assert forbidden not in d
        assert not hasattr(fx.plans, "execute") and not hasattr(fx.plans, "run")
    for t in tasks(fx):
        d = t.to_dict()
        for forbidden in ("execute", "run", "agent", "job", "process", "autonomous", "invoke"):
            assert forbidden not in d
        assert not hasattr(fx.tasks, "execute") and not hasattr(fx.tasks, "run")


def test_unapproved_plan_readiness_blocked_by_policy():
    """If the readiness policy denies, the plan cannot become READY (approval still ok)."""
    from backend.policy_engine import (
        install_default_plan_policies, plan_policy_decider,
        ConstraintType, ConstraintCategory, PolicyRule,
    )
    from backend.planning_foundation import (
        PlanService, PlanMetadata, PlanCategory, PlanGovernanceError,
    )
    from _v4_helpers import build_v4, goals as goal_records

    base = build_v4(1)
    ps = base.policies
    tracker = base.tracker
    g = goal_records(base)[0]
    hooks = install_default_plan_policies(ps)

    # replace the readiness policy with one that DENIES (forbidden constraint always applies)
    c = ps.create_constraint(constraint_type=ConstraintType.FORBIDDEN.value,
                             category=ConstraintCategory.PROHIBITION, subject_kind="plan",
                             constraint_key="deny_readiness", rules=())
    deny = ps.create_policy(category="obligation", policy_key="plan_readiness_deny",
                            title="Deny Readiness", description="denies readiness",
                            subject_kind="plan",
                            rules=(PolicyRule("m", "hook", "eq", "plan_readiness"),),
                            constraint_ids=(c.constraint_id,))
    ps.activate(deny, authority="gov")
    hooks["plan_readiness"] = deny.policy_id

    decider = plan_policy_decider(ps, hooks)
    svc = PlanService(lineage_tracker=tracker, policy_decider=decider)
    p = svc.create_plan(category=PlanCategory.WORKFLOW, plan_key="k",
                        metadata=PlanMetadata(title="T", approach="a", expected_outcome="o"),
                        source_goal_id=g.goal_id, source_goal_lineage_id=g.lineage_id,
                        source_goal_state=g.state.value)
    svc.transition(p, PlanLifecycleState.DRAFT)
    svc.transition(p, PlanLifecycleState.UNDER_REVIEW)
    svc.transition(p, PlanLifecycleState.APPROVED)              # approval policy permits
    assert p.state == PlanLifecycleState.APPROVED
    try:
        svc.transition(p, PlanLifecycleState.READY)
        assert False, "readiness should have been denied by policy"
    except PlanGovernanceError:
        pass
    assert p.state != PlanLifecycleState.READY


def test_full_chain_is_reproducible():
    def run():
        fx = build_v4b(2)
        p_sigs = sorted(p.state_signature() for p in plans(fx))
        t_sigs = sorted(t.state_signature() for t in tasks(fx))
        return (p_sigs, t_sigs, fx.plans.audit.head, fx.tasks.audit.head)
    assert run() == run()
