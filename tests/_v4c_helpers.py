"""Shared builders for the V4-P5 / V4-P6 test suites.

Extends the V4-P3/P4 fixture (`build_v4b`) with the Agent Coordination Framework
(V4-P5) and the Execution Orchestration Layer (V4-P6), wired together via the
agent-policy and execution-policy deciders, all over the one shared platform lineage
tracker.

For each READY task: an Agent is created (and driven to AVAILABLE), the agent is
assigned to the task (capability-matched), and an Execution is created referencing
that approved assignment and driven to COMPLETED. Because an assignment parents the
agent + task lineage nodes and an execution parents the assignment node, every
execution traces back through agent/assignment -> task -> plan -> goal ->
recommendation/analytics -> ... -> patient. Not collected by pytest (no ``test_``).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v4b_helpers import build_v4b, goals as _goals, plans as _plans, tasks as _tasks, V4bFixture

from backend.policy_engine import (
    install_default_agent_policies, agent_policy_decider,
    install_default_execution_policies, execution_policy_decider,
)
from backend.agent_coordination import (
    AgentService, AgentMetadata, AgentCapability, AgentCategory, AgentPriority,
    AgentLifecycleState, CapabilityRisk, CapabilityMode,
)
from backend.execution_orchestration import (
    ExecutionService, ExecutionMetadata, ExecutionContext, ExecutionAssignment,
    ExecutionLifecycleState,
)


@dataclass
class V4cFixture:
    base: V4bFixture
    tracker: object
    agents: AgentService
    agent_records: dict          # agent_id -> AVAILABLE AgentRecord
    agent_hooks: dict
    assignments: dict            # task_id -> AgentAssignment
    executions: ExecutionService
    execution_records: dict      # execution_id -> COMPLETED ExecutionRecord
    execution_hooks: dict


_AGENT_STATES = (AgentLifecycleState.DRAFT, AgentLifecycleState.UNDER_REVIEW,
                 AgentLifecycleState.APPROVED, AgentLifecycleState.AVAILABLE)
_EXEC_STATES = (ExecutionLifecycleState.QUEUED, ExecutionLifecycleState.AUTHORIZED,
                ExecutionLifecycleState.ACTIVE, ExecutionLifecycleState.COMPLETED)
_REVIEW_CAP = "review_work"


def build_v4c(n_cases: int = 2, *, drive: bool = True) -> V4cFixture:
    base = build_v4b(n_cases)
    tracker = base.tracker
    ps = base.base.policies

    # --- V4-P5 agents (policy-governed), assigned to READY tasks ------------
    agent_hooks = install_default_agent_policies(ps)
    asvc = AgentService(lineage_tracker=tracker, policy_decider=agent_policy_decider(ps, agent_hooks))

    agent_records: dict = {}
    assignments: dict = {}
    for i, task in enumerate(_tasks(base)):
        agent = asvc.create_agent(
            category=AgentCategory.SYSTEM, agent_key=f"agent-for-{task.task_key}",
            metadata=AgentMetadata(title=f"Agent {i}", role="reviewer participant"),
            capabilities=(AgentCapability(name=_REVIEW_CAP, mode=CapabilityMode.ALLOWED,
                                          risk=CapabilityRisk.MODERATE,
                                          description="may review work"),),
            priority=AgentPriority.HIGH)
        if drive:
            for st in _AGENT_STATES:
                asvc.transition(agent, st, reason=st.value)
            asn = asvc.assign(agent, target_id=task.task_id, target_kind="task",
                              required_capabilities=[_REVIEW_CAP], target_lineage_id=task.lineage_id)
            assignments[task.task_id] = asn
        agent_records[agent.agent_id] = agent

    # --- V4-P6 executions (policy-governed), progressing approved assignments -
    exec_hooks = install_default_execution_policies(ps)
    esvc = ExecutionService(lineage_tracker=tracker,
                            policy_decider=execution_policy_decider(ps, exec_hooks))

    execution_records: dict = {}
    if drive:
        for task in _tasks(base):
            asn = assignments[task.task_id]
            ctx = ExecutionContext(goal_id=task.source_goal_id, plan_id=task.source_plan_id,
                                   task_id=task.task_id, agent_id=asn.agent_id,
                                   assignment_id=asn.assignment_id)
            easn = ExecutionAssignment(assignment_id=asn.assignment_id, agent_id=asn.agent_id,
                                       task_id=task.task_id, assignment_state=asn.state)
            ex = esvc.create_execution(
                execution_key=f"exec-for-{task.task_key}",
                metadata=ExecutionMetadata(title=f"Execution for {task.metadata.title}",
                                           objective="progress the approved task"),
                context=ctx, assignment=easn, assignment_lineage_id=asn.lineage_id)
            for st in _EXEC_STATES:
                esvc.transition(ex, st, reason=st.value)
            execution_records[ex.execution_id] = ex

    return V4cFixture(base=base, tracker=tracker, agents=asvc, agent_records=agent_records,
                      agent_hooks=agent_hooks, assignments=assignments, executions=esvc,
                      execution_records=execution_records, execution_hooks=exec_hooks)


def goals(fx: V4cFixture) -> list:
    return _goals(fx.base)


def plans(fx: V4cFixture) -> list:
    return _plans(fx.base)


def tasks(fx: V4cFixture) -> list:
    return _tasks(fx.base)


def agents(fx: V4cFixture) -> list:
    return list(fx.agent_records.values())


def executions(fx: V4cFixture) -> list:
    return list(fx.execution_records.values())
