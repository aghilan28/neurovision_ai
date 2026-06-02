"""Shared builders for the V4-P3 / V4-P4 test suites.

Extends the V4-P1/P2 fixture (`build_v4`) with the Planning Foundation (V4-P3) and
the Task Intelligence Layer (V4-P4), wired together via the plan-policy and
task-policy deciders, all over the one shared platform lineage tracker.

For each ACTIVE goal a Plan is derived (and driven to READY); for each READY plan a
Task is derived (and driven to READY). Because a plan parents the goal's lineage node
and a task parents the plan's, every task traces back through plan -> goal ->
recommendation/analytics -> ... -> patient. Not collected by pytest (no ``test_``).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v4_helpers import build_v4, goals as _goals, V4Fixture

from backend.policy_engine import (
    install_default_plan_policies, plan_policy_decider,
    install_default_task_policies, task_policy_decider,
)
from backend.planning_foundation import (
    PlanService, PlanMetadata, PlanCategory, PlanPriority, PlanLifecycleState,
)
from backend.task_intelligence import (
    TaskService, TaskMetadata, TaskCategory, TaskPriority, TaskLifecycleState,
)


@dataclass
class V4bFixture:
    base: V4Fixture
    tracker: object
    plans: PlanService
    plan_records: dict          # plan_id -> READY PlanRecord
    plan_hooks: dict
    plan_decider: object
    tasks: TaskService
    task_records: dict          # task_id -> READY TaskRecord
    task_hooks: dict
    task_decider: object


_PLAN_STATES = (PlanLifecycleState.DRAFT, PlanLifecycleState.UNDER_REVIEW,
                PlanLifecycleState.APPROVED, PlanLifecycleState.READY)
_TASK_STATES = (TaskLifecycleState.DRAFT, TaskLifecycleState.UNDER_REVIEW,
                TaskLifecycleState.APPROVED, TaskLifecycleState.READY)


def build_v4b(n_cases: int = 2, *, drive: bool = True) -> V4bFixture:
    base = build_v4(n_cases)
    tracker = base.tracker
    ps = base.policies

    # --- V4-P3 plans (policy-governed), derived from ACTIVE goals ------------
    plan_hooks = install_default_plan_policies(ps)
    plan_decider = plan_policy_decider(ps, plan_hooks)
    plan_svc = PlanService(lineage_tracker=tracker, policy_decider=plan_decider)

    plan_records: dict = {}
    for i, g in enumerate(_goals(base)):
        plan = plan_svc.create_plan(
            category=PlanCategory.WORKFLOW, plan_key=f"plan-for-{g.definition_key}",
            metadata=PlanMetadata(title=f"Plan for {g.metadata.title}",
                                  approach="structured work breakdown",
                                  expected_outcome=g.metadata.desired_outcome),
            source_goal_id=g.goal_id, source_goal_lineage_id=g.lineage_id,
            source_goal_state=g.state.value, priority=PlanPriority.HIGH)
        # a plan -> goal relationship (supports the goal it derives from)
        plan_svc.relate(plan, relation="supports", target_id=g.goal_id, target_kind="goal",
                        target_lineage_id=g.lineage_id)
        if drive:
            for st in _PLAN_STATES:
                plan_svc.transition(plan, st, reason=st.value)
        plan_records[plan.plan_id] = plan

    # --- V4-P4 tasks (policy-governed), derived from READY plans ------------
    task_hooks = install_default_task_policies(ps)
    task_decider = task_policy_decider(ps, task_hooks)
    task_svc = TaskService(lineage_tracker=tracker, policy_decider=task_decider)

    task_records: dict = {}
    for plan in plan_records.values():
        task = task_svc.create_task(
            category=TaskCategory.WORKFLOW, task_key=f"task-for-{plan.plan_key}",
            metadata=TaskMetadata(title=f"Task for {plan.metadata.title}",
                                  work_definition="atomic unit of work for the plan"),
            source_plan_id=plan.plan_id, source_plan_lineage_id=plan.lineage_id,
            source_plan_state=plan.state.value, source_goal_id=plan.source_goal_id,
            priority=TaskPriority.HIGH)
        task_svc.relate(task, relation="derived_from", target_id=plan.plan_id,
                        target_kind="plan", target_lineage_id=plan.lineage_id)
        if drive:
            for st in _TASK_STATES:
                task_svc.transition(task, st, reason=st.value)
        task_records[task.task_id] = task

    return V4bFixture(base=base, tracker=tracker, plans=plan_svc, plan_records=plan_records,
                      plan_hooks=plan_hooks, plan_decider=plan_decider, tasks=task_svc,
                      task_records=task_records, task_hooks=task_hooks, task_decider=task_decider)


def goals(fx: V4bFixture) -> list:
    return _goals(fx.base)


def plans(fx: V4bFixture) -> list:
    return list(fx.plan_records.values())


def tasks(fx: V4bFixture) -> list:
    return list(fx.task_records.values())
