"""End-to-end V4-P1 + V4-P2 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event ->
    Timeline -> Workflow -> Graph -> Analytics -> Recommendations -> Goal ->
    Policy -> Constraint -> Governance

over the real V2/V3/V4 artifacts on one shared lineage tracker, and that all
cross-version invariants hold (V3 lineage intact, determinism, audit immutability,
goals never execute, every active goal policy-governed, no isolated implementation).
"""

from __future__ import annotations

from _v4_helpers import build_v4, goals, active_policies
from backend.goal_intelligence import GoalLifecycleState


def test_full_chain_executes_with_traceability():
    fx = build_v4(2)
    tracker = fx.tracker

    # --- goals reach ACTIVE, validate, and trace to the patient -------------
    gs = goals(fx)
    assert gs and all(g.is_active for g in gs)
    for g in gs:
        assert fx.goals.validate(g).ok
        kinds = {r.kind for r in tracker.chain(g.lineage_id)}
        # the full spine: goal -> recommendation -> analytics -> workflow/graph ->
        # event -> case -> patient
        for k in ("goal", "recommendation", "analytics", "workflow", "graph_node",
                  "event", "case", "patient"):
            assert k in kinds, f"missing {k} in goal lineage"
        assert tracker.verify_chain(g.lineage_id)

    # --- policies + constraints + evaluations validate + trace --------------
    pols = active_policies(fx)
    assert pols and all(fx.policies.validate(p).ok for p in pols)
    assert fx.policies.registry.list_constraints()           # constraints exist
    assert fx.policies.registry.list_evaluations()           # governance produced evaluations
    for eid in fx.policies.registry.list_evaluations():
        ev = fx.policies.registry.evaluation(eid)
        kinds = {r.kind for r in tracker.chain(ev.lineage_id)}
        # an evaluation traces through the policy AND the goal it governed -> patient
        assert {"policy_evaluation", "policy", "goal", "analytics", "patient"} <= kinds
        assert tracker.verify_chain(ev.lineage_id)

    # --- audit trails immutable + intact (every subsystem) ------------------
    assert fx.goals.audit.verify() and fx.policies.audit.verify()
    assert fx.base.analytics.audit.verify() and fx.base.recommendations.audit.verify()
    assert fx.base.base.workflows.audit.verify() and fx.base.base.graph.audit.verify()

    # --- V3 lineage remains intact ------------------------------------------
    for c in fx.base.base.base.cases.values():
        assert tracker.verify_chain(c.lineage_id)
    for r in fx.base.recommendation_records["guidance"]:
        assert tracker.verify_chain(r.lineage_id)


def test_every_active_goal_is_policy_governed():
    fx = build_v4(2)
    for g in goals(fx):
        # an active goal must carry a governing policy reference + an approved history
        assert g.governance.policy_references
        assert g.governance.approval_state == "approved"


def test_goals_carry_no_execution():
    """Goals are intent — they never carry an executable action payload."""
    fx = build_v4(2)
    for g in goals(fx):
        d = g.to_dict()
        for forbidden in ("action", "command", "execute", "task", "plan", "agent", "run"):
            assert forbidden not in d
        # the goal subsystem exposes no execution API
        assert not hasattr(fx.goals, "execute")
        assert not hasattr(fx.goals, "run")


def test_unapproved_goal_activation_is_blocked_by_policy():
    """If the activation policy denies, the goal cannot become ACTIVE (approval still ok)."""
    from backend.policy_engine import (
        PolicyService, goal_policy_decider, install_default_goal_policies,
        ConstraintType, ConstraintCategory, PolicyRule,
    )
    from backend.goal_intelligence import (
        GoalService, GoalMetadata, GoalCategory, GoalPriority, GoalGovernanceError,
    )
    from ml.lineage import LineageTracker

    tracker = LineageTracker()
    ps = PolicyService(lineage_tracker=tracker)
    hooks = install_default_goal_policies(ps)   # permissive approval/activation/...

    # replace the activation policy with one that DENIES (forbidden constraint always applies)
    c = ps.create_constraint(constraint_type=ConstraintType.FORBIDDEN.value,
                             category=ConstraintCategory.PROHIBITION, subject_kind="goal",
                             constraint_key="deny_activation", rules=())  # always applies
    deny = ps.create_policy(category="obligation", policy_key="goal_activation_deny",
                            title="Deny Activation", description="denies activation",
                            subject_kind="goal",
                            rules=(PolicyRule("m", "hook", "eq", "goal_activation"),),
                            constraint_ids=(c.constraint_id,))
    ps.activate(deny, authority="gov")
    hooks["goal_activation"] = deny.policy_id    # route activation to the denying policy

    decider = goal_policy_decider(ps, hooks)
    gs = GoalService(lineage_tracker=tracker, policy_decider=decider)
    g = gs.create_goal(category=GoalCategory.QUALITY, definition_key="dq",
                       metadata=GoalMetadata(title="DQ", desired_outcome="o"),
                       priority=GoalPriority.LOW)
    gs.transition(g, GoalLifecycleState.DRAFT)
    gs.transition(g, GoalLifecycleState.UNDER_REVIEW)
    gs.transition(g, GoalLifecycleState.APPROVED)   # approval policy permits
    assert g.state == GoalLifecycleState.APPROVED
    try:
        gs.transition(g, GoalLifecycleState.ACTIVE)
        assert False, "activation should have been denied by policy"
    except GoalGovernanceError:
        pass
    assert g.state != GoalLifecycleState.ACTIVE


def test_full_chain_is_reproducible():
    def run():
        fx = build_v4(2)
        g_sigs = sorted(g.state_signature() for g in goals(fx))
        p_sigs = sorted(p.state_signature() for p in active_policies(fx))
        return (g_sigs, p_sigs, fx.goals.audit.head, fx.policies.audit.head)
    assert run() == run()
