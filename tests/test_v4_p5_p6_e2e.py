"""End-to-end V4-P5 + V4-P6 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event ->
    Timeline -> Workflow -> Graph -> Analytics -> Recommendations -> Goal ->
    Policy -> Constraint -> Plan -> Task -> Agent -> Execution -> Governance

over the real V2/V3/V4 artifacts on one shared lineage tracker, and that all
cross-version invariants hold (V4 goal-policy-plan-task lineage intact, determinism,
audit immutability, agents hold no autonomous authority, executions never bypass
governance, every assignment satisfies capability requirements).
"""

from __future__ import annotations

from _v4c_helpers import build_v4c, goals, plans, tasks, agents, executions
from backend.execution_orchestration import ExecutionLifecycleState


def test_full_chain_executes_with_traceability():
    fx = build_v4c(2)
    tracker = fx.tracker

    # --- agents reach AVAILABLE, validate, and (via assignment) trace to patient -
    ags = agents(fx)
    assert ags and all(a.is_available for a in ags)
    for a in ags:
        assert fx.agents.validate(a).ok

    # --- executions reach COMPLETED, validate, and trace to the patient -----
    exs = executions(fx)
    assert exs and all(e.state == ExecutionLifecycleState.COMPLETED for e in exs)
    for e in exs:
        assert fx.executions.validate(e).ok
        kinds = {r.kind for r in tracker.chain(e.lineage_id)}
        for k in ("execution", "agent_assignment", "agent", "task", "plan", "goal",
                  "recommendation", "analytics", "workflow", "event", "case", "patient"):
            assert k in kinds, f"missing {k} in execution lineage"
        assert tracker.verify_chain(e.lineage_id)

    # --- audit trails immutable + intact (every subsystem) ------------------
    assert fx.agents.audit.verify() and fx.executions.audit.verify()
    assert fx.base.plans.audit.verify() and fx.base.tasks.audit.verify()
    assert fx.base.base.goals.audit.verify() and fx.base.base.policies.audit.verify()

    # --- V4 goal-policy-plan-task lineage remains intact --------------------
    for g in goals(fx):
        assert tracker.verify_chain(g.lineage_id) and fx.base.base.goals.validate(g).ok
    for p in plans(fx):
        assert tracker.verify_chain(p.lineage_id) and fx.base.plans.validate(p).ok
    for t in tasks(fx):
        assert tracker.verify_chain(t.lineage_id) and fx.base.tasks.validate(t).ok


def test_every_available_agent_and_active_execution_is_policy_governed():
    fx = build_v4c(2)
    for a in agents(fx):
        assert a.governance.policy_references and a.governance.approval_state == "approved"
    for e in executions(fx):
        assert e.governance.policy_references
        assert e.governance.authorization_state == "authorized"


def test_agents_hold_no_autonomous_authority():
    """Agents describe capability; they are not autonomous/self-modifying/unbounded."""
    fx = build_v4c(2)
    for a in agents(fx):
        d = a.to_dict()
        for forbidden in ("autonomous", "self_modify", "unbounded", "execute", "run"):
            assert forbidden not in d
        assert not hasattr(fx.agents, "execute") and not hasattr(fx.agents, "run")


def test_executions_never_bypass_governance():
    """An execution cannot become ACTIVE without authorization (policy-governed)."""
    from backend.policy_engine import (
        install_default_execution_policies, execution_policy_decider,
        ConstraintType, ConstraintCategory, PolicyRule,
    )
    from backend.execution_orchestration import (
        ExecutionService, ExecutionMetadata, ExecutionContext, ExecutionAssignment,
    )
    fx = build_v4c(1)
    ps = fx.base.base.policies
    tracker = fx.tracker
    task = tasks(fx)[0]
    asn = fx.assignments[task.task_id]

    hooks = install_default_execution_policies(ps)
    # replace the activation policy with one that DENIES (forbidden constraint always applies)
    c = ps.create_constraint(constraint_type=ConstraintType.FORBIDDEN.value,
                             category=ConstraintCategory.PROHIBITION, subject_kind="execution",
                             constraint_key="deny_activation", rules=())
    deny = ps.create_policy(category="obligation", policy_key="execution_activation_deny",
                            title="Deny Activation", description="denies activation",
                            subject_kind="execution",
                            rules=(PolicyRule("m", "hook", "eq", "execution_activation"),),
                            constraint_ids=(c.constraint_id,))
    ps.activate(deny, authority="gov")
    hooks["execution_activation"] = deny.policy_id

    svc = ExecutionService(lineage_tracker=tracker,
                           policy_decider=execution_policy_decider(ps, hooks))
    ctx = ExecutionContext(goal_id=task.source_goal_id, plan_id=task.source_plan_id,
                           task_id=task.task_id, agent_id=asn.agent_id,
                           assignment_id=asn.assignment_id)
    easn = ExecutionAssignment(assignment_id=asn.assignment_id, agent_id=asn.agent_id,
                               task_id=task.task_id, assignment_state=asn.state)
    ex = svc.create_execution(execution_key="denied-run",
                              metadata=ExecutionMetadata(title="T", objective="o"),
                              context=ctx, assignment=easn, assignment_lineage_id=asn.lineage_id)
    svc.transition(ex, ExecutionLifecycleState.QUEUED)
    svc.transition(ex, ExecutionLifecycleState.AUTHORIZED, approved=True)
    import pytest
    from backend.execution_orchestration import ExecutionGovernanceError
    with pytest.raises(ExecutionGovernanceError):
        svc.transition(ex, ExecutionLifecycleState.ACTIVE)
    assert ex.state != ExecutionLifecycleState.ACTIVE


def test_full_chain_is_reproducible():
    def run():
        fx = build_v4c(2)
        a_sigs = sorted(a.state_signature() for a in agents(fx))
        e_sigs = sorted(e.state_signature() for e in executions(fx))
        return (a_sigs, e_sigs, fx.agents.audit.head, fx.executions.audit.head)
    assert run() == run()
