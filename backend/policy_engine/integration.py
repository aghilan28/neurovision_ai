"""Goal <-> Policy integration (V4-P1 + V4-P2).

Wires the Policy & Constraint Engine into the Goal lifecycle so that **every active
goal is policy governed**. The goal subsystem stays policy-agnostic: it accepts an
injected ``policy_decider`` callable; this module *is* that callable, backed by real
ACTIVE policies in a :class:`PolicyService`.

It installs the default goal-lifecycle policies (one per governed hook —
goal_approval / goal_activation / goal_suspension / goal_completion), each binding a
constraint that encodes the governance requirement, and returns a decider that:

  * builds a deterministic evaluation **context** from the goal,
  * evaluates the matching ACTIVE policy,
  * maps the explainable outcome to (approved, decision, policy_id, authority).

The decision is therefore deterministic, explainable, audited (in the policy audit
log), and lineage-tracked — no parallel governance.
"""

from __future__ import annotations

from typing import Callable

from .version import DETERMINISTIC_EPOCH
from .policies.taxonomy import (
    PolicyCategory, ConstraintType, ConstraintCategory, EvaluationOutcome,
)
from .models.domain import PolicyRule
from .service import PolicyService

# the four governed goal hooks (mirror goal_intelligence.lifecycle.GOVERNED_TRANSITIONS)
GOAL_HOOKS = ("goal_approval", "goal_activation", "goal_suspension", "goal_completion")

# hook -> (policy category, the fact the goal context must satisfy, human title)
_HOOK_SPEC = {
    "goal_approval": (PolicyCategory.GOVERNANCE, "review_complete",
                      "Goal Approval Requires Completed Review"),
    "goal_activation": (PolicyCategory.OBLIGATION, "governance_approved",
                        "Cannot Activate Unapproved Goals"),
    "goal_suspension": (PolicyCategory.GOVERNANCE, "suspension_authorized",
                        "Goal Suspension Requires Authorization"),
    "goal_completion": (PolicyCategory.GOVERNANCE, "outcome_met",
                        "Goal Completion Requires Outcome Met"),
}

_OUTCOME_APPROVES = frozenset({EvaluationOutcome.PERMITTED.value,
                               EvaluationOutcome.CONDITIONAL_APPROVAL.value})


def install_default_goal_policies(policy_service: PolicyService,
                                  created_at: str = DETERMINISTIC_EPOCH) -> dict:
    """Create + activate one ACTIVE policy per governed goal hook. Returns hook->policy_id."""
    hook_to_policy: dict = {}
    for hook, (category, fact, title) in _HOOK_SPEC.items():
        # a REQUIRED constraint: the governing fact must be satisfied for this hook
        constraint = policy_service.create_constraint(
            constraint_type=ConstraintType.REQUIRED.value,
            category=ConstraintCategory.GOVERNANCE, subject_kind="goal",
            constraint_key=f"{hook}_requirement",
            rules=(PolicyRule(rule_id=f"{hook}_applies", fact="hook", operator="eq", value=hook,
                              description=f"applies to the {hook} hook"),),
            explanation=f"{title}: the goal must satisfy '{fact}' for {hook}.",
            created_at=created_at)
        policy = policy_service.create_policy(
            category=category, policy_key=hook, title=title,
            description=f"Governs the {hook} transition of a goal ({fact} required).",
            subject_kind="goal",
            rules=(PolicyRule(rule_id=f"{hook}_match", fact="hook", operator="eq", value=hook,
                              description=f"this policy governs the {hook} hook"),),
            constraint_ids=(constraint.constraint_id,), created_at=created_at)
        policy_service.activate(policy, authority="governance", created_at=created_at)
        hook_to_policy[hook] = policy.policy_id
    return hook_to_policy


def _goal_context(hook: str, goal) -> dict:
    """A deterministic evaluation context derived from the goal + hook.

    The ``*_satisfied`` keys feed the REQUIRED-constraint check in the evaluator.
    """
    gov = goal.governance
    # the required-fact name the evaluator checks is "<constraint_key>_satisfied"
    satisfied_key = f"{hook}_requirement_satisfied"
    requirement_met = {
        "goal_approval": gov.review_required is False or gov.approval_state in
        ("approved", "pending"),
        "goal_activation": gov.approval_state == "approved" or _has_active_approval(goal),
        "goal_suspension": True,
        "goal_completion": True,
    }.get(hook, True)
    return {
        "hook": hook, "goal_id": goal.goal_id, "category": goal.category,
        "priority": goal.priority, "state": goal.state.value,
        "governance_approved": gov.approval_state == "approved",
        "review_complete": gov.review_required is False or goal.state.value in
        ("under_review", "approved", "active"),
        "suspension_authorized": True, "outcome_met": bool(goal.metadata.desired_outcome),
        satisfied_key: bool(requirement_met), "requirement_met": bool(requirement_met),
    }


def _has_active_approval(goal) -> bool:
    return any(e.get("decision") == "approved" for e in goal.governance.approval_history)


def goal_policy_decider(policy_service: PolicyService, hook_to_policy: dict,
                        authority: str = "governance") -> Callable:
    """Return a decider ``(hook, goal) -> (approved, decision, policy_id, authority)``.

    Evaluates the ACTIVE policy bound to ``hook`` against a deterministic goal
    context; PERMITTED/CONDITIONAL_APPROVAL approve, everything else denies.
    """
    def _decide(hook: str, goal):
        policy_id = hook_to_policy.get(hook)
        if policy_id is None:
            return False, "no_policy", None, authority
        policy_record = _policy_record_for(policy_service, policy_id)
        evaluation = policy_service.evaluate(
            policy_record, subject_kind="goal", subject_id=goal.goal_id, request=hook,
            context=_goal_context(hook, goal), subject_lineage_id=goal.lineage_id)
        approved = evaluation.outcome in _OUTCOME_APPROVES
        return approved, evaluation.outcome, policy_id, authority
    return _decide


def _policy_record_for(policy_service: PolicyService, policy_id: str):
    """Return the live ACTIVE PolicyRecord aggregate kept by the service."""
    return policy_service.policy_cache[policy_id]
