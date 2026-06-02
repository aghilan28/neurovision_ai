"""Shared builders for the V4-P1 / V4-P2 test suites.

Extends the V3-P5/P6 fixture (`build_v3c`) with the Policy & Constraint Engine
(V4-P2) and the Goal Intelligence Foundation (V4-P1), wired together via the
goal-policy decider, all over the one shared platform lineage tracker. A goal is
created `derived_from` a real recommendation + analytics node so it traces back
through the full V3 chain to the patient. Not collected by pytest (no ``test_``).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v3c_helpers import build_v3c, all_recommendations, V3cFixture

from backend.policy_engine import (
    PolicyService, install_default_goal_policies, goal_policy_decider,
)
from backend.goal_intelligence import (
    GoalService, GoalMetadata, GoalCategory, GoalPriority, GoalLifecycleState,
)


@dataclass
class V4Fixture:
    base: V3cFixture
    tracker: object
    policies: PolicyService
    hook_to_policy: dict
    goals: GoalService
    goal_records: dict          # goal_id -> active GoalRecord
    decider: object


# (category, definition_key, title, desired_outcome, priority)
_GOAL_PLAN = [
    (GoalCategory.WORKFLOW, "reduce-review-latency", "Reduce Review Latency",
     "lower review latency", GoalPriority.HIGH),
    (GoalCategory.RISK, "reduce-bottleneck-risk", "Reduce Bottleneck Risk",
     "lower bottleneck risk", GoalPriority.CRITICAL),
    (GoalCategory.KNOWLEDGE, "improve-knowledge-coverage", "Improve Knowledge Coverage",
     "broader knowledge coverage", GoalPriority.MEDIUM),
]


def build_v4(n_cases: int = 2, *, activate: bool = True) -> V4Fixture:
    base = build_v3c(n_cases)
    tracker = base.base.base.cs.lineage          # single shared platform lineage tracker

    # --- V4-P2 policy engine + default governed goal policies ----------------
    ps = PolicyService(lineage_tracker=tracker)
    hook_to_policy = install_default_goal_policies(ps)
    decider = goal_policy_decider(ps, hook_to_policy)

    # --- V4-P1 goals (policy-governed), derived from V3 intelligence ---------
    gs = GoalService(lineage_tracker=tracker, policy_decider=decider)
    recs = all_recommendations(base)
    rec = recs[0] if recs else None
    risk = base.analytics_records["risk"]

    goal_records: dict = {}
    for i, (category, key, title, outcome, priority) in enumerate(_GOAL_PLAN):
        derived = [risk.lineage_id]
        if rec is not None:
            derived.append(rec.lineage_id)
        g = gs.create_goal(category=category, definition_key=key,
                           metadata=GoalMetadata(title=title, desired_outcome=outcome),
                           priority=priority, derived_from=derived)
        # relate the goal to the upstream intelligence it derives from
        gs.relate(g, relation="influences", target_id=risk.analytics_id,
                  target_kind="analytics", target_lineage_id=risk.lineage_id)
        if rec is not None:
            gs.relate(g, relation="derived_from", target_id=rec.recommendation_id,
                      target_kind="recommendation", target_lineage_id=rec.lineage_id)
        if activate:
            for st in (GoalLifecycleState.DRAFT, GoalLifecycleState.UNDER_REVIEW,
                       GoalLifecycleState.APPROVED, GoalLifecycleState.ACTIVE):
                gs.transition(g, st, reason=st.value)
        goal_records[g.goal_id] = g

    return V4Fixture(base=base, tracker=tracker, policies=ps, hook_to_policy=hook_to_policy,
                     goals=gs, goal_records=goal_records, decider=decider)


def goals(fx: V4Fixture) -> list:
    return list(fx.goal_records.values())


def active_policies(fx: V4Fixture) -> list:
    return [fx.policies.policy_cache[pid] for pid in fx.policies.registry.active_policies()]
