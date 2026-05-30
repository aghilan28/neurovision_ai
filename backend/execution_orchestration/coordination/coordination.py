"""Execution coordination (V4-P6).

Deterministic, read-only helpers that *coordinate* an execution with the
already-approved upstream artifacts it references — goal, plan, task, agent,
assignment, policies, constraints. Coordination **references** existing approved
artifacts; it never creates, plans, or modifies them (no autonomous planning).

The coordinator answers preconditions the service checks before an execution may be
authorized/activated, e.g. "does this execution reference a complete, consistent
context (task + agent + approved assignment)?".
"""

from __future__ import annotations

from typing import Optional

# the assignment states from which an execution may legitimately progress work.
_PROGRESSABLE_ASSIGNMENT_STATES = frozenset({"assigned"})


def context_complete(context) -> tuple[bool, list]:
    """Whether the execution context binds the minimal approved artifacts.

    Returns (ok, missing). A coordinated execution must reference a task, an agent,
    and an assignment (it progresses an approved assignment of an agent to a task).
    """
    missing = []
    if not context.task_id:
        missing.append("task_id")
    if not context.agent_id:
        missing.append("agent_id")
    if not context.assignment_id:
        missing.append("assignment_id")
    return (len(missing) == 0), missing


def assignment_consistent(context, assignment) -> tuple[bool, str]:
    """Whether the referenced assignment matches the context (agent + task + id)."""
    if assignment.assignment_id != context.assignment_id:
        return False, "assignment id mismatch with context"
    if assignment.agent_id != context.agent_id:
        return False, "assignment agent mismatch with context"
    if assignment.task_id != context.task_id:
        return False, "assignment task mismatch with context"
    return True, "consistent"


def assignment_progressable(assignment_state: str) -> bool:
    """An execution may progress only an actively-assigned assignment (not revoked/blocked)."""
    return assignment_state in _PROGRESSABLE_ASSIGNMENT_STATES


def coordination_parents(context, assignment_lineage_id: Optional[str]) -> tuple:
    """Lineage parents for an execution: the approved assignment node (-> agent/task/...).

    Parenting on the assignment node makes the execution trace back through the
    assignment to the agent and the task, and through the task to the patient.
    """
    return tuple(p for p in (assignment_lineage_id,) if p)


def coordination_summary(context) -> dict:
    ok, missing = context_complete(context)
    return {"context_complete": ok, "missing": missing,
            "references": {"goal_id": context.goal_id, "plan_id": context.plan_id,
                           "task_id": context.task_id, "agent_id": context.agent_id,
                           "assignment_id": context.assignment_id},
            "n_policy_references": len(context.policy_references),
            "n_constraint_references": len(context.constraint_references)}
