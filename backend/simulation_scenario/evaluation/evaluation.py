"""Simulation evaluation engine (V4-P9).

Deterministically evaluates the effect dimensions of a scenario from its observed
context: policy effects, constraint effects, task dependencies, agent availability,
execution structures, and governance controls. Produces a :class:`SimulationOutcome`
per dimension — **no randomness**; the same context (and assumptions) always yields
identical outcomes. Evaluation observes; it never executes or mutates anything.

Declarative what-if **assumptions** are applied only inside the evaluation (never to
production):
  * ``exclude_agents``      : [agent_id, ...]      — treat those agents as unavailable
  * ``blocked_executions``  : [execution_id, ...]  — treat those executions as blocked
  * ``strict_policies``     : bool                 — require every entity to be policy-governed
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import SimulationOutcome, SimDimension, OutcomeStatus
from ..models.context import ScenarioContext, observations_from_context

# kinds that are themselves governance artifacts (excluded from policy-coverage checks).
_GOV_KINDS = ("policy", "constraint")


def _status_for(score: float) -> str:
    if score >= 0.8:
        return OutcomeStatus.READY
    if score >= 0.5:
        return OutcomeStatus.DEGRADED
    return OutcomeStatus.BLOCKED


def _outcome(dimension: str, score: float, detail: str, metrics: dict) -> SimulationOutcome:
    score = round(max(0.0, min(1.0, score)), 6)
    return SimulationOutcome(dimension=dimension, status=_status_for(score), score=score,
                             detail=detail, metrics=metrics)


def _policy_effects(obs: Sequence, assumptions: dict) -> SimulationOutcome:
    governed = [o for o in obs if o.kind not in _GOV_KINDS]
    total = len(governed) or 1
    with_policy = sum(1 for o in governed if o.policy_references)
    score = with_policy / total
    if assumptions.get("strict_policies") and with_policy < len(governed):
        score = min(score, 0.49)
    return _outcome(SimDimension.POLICY_EFFECTS, score,
                    f"{with_policy}/{len(governed)} governed entities reference a policy",
                    {"governed": len(governed), "with_policy": with_policy,
                     "strict": bool(assumptions.get("strict_policies"))})


def _constraint_effects(obs: Sequence) -> SimulationOutcome:
    total = len(obs) or 1
    satisfied = sum(1 for o in obs if o.approved)
    score = satisfied / total
    return _outcome(SimDimension.CONSTRAINT_EFFECTS, score,
                    f"{satisfied}/{len(obs)} entities have constraints satisfied (approved)",
                    {"total": len(obs), "satisfied": satisfied})


def _task_dependencies(obs: Sequence) -> SimulationOutcome:
    tasks = [o for o in obs if o.kind == "task"]
    if not tasks:
        return _outcome(SimDimension.TASK_DEPENDENCIES, 1.0, "no tasks in scope", {"n_tasks": 0})
    ready = sum(1 for t in tasks if t.approved and t.live)
    score = ready / len(tasks)
    return _outcome(SimDimension.TASK_DEPENDENCIES, score,
                    f"{ready}/{len(tasks)} tasks have dependencies met (ready)",
                    {"n_tasks": len(tasks), "ready": ready})


def _agent_availability(obs: Sequence, assumptions: dict) -> SimulationOutcome:
    agents = [o for o in obs if o.kind == "agent"]
    if not agents:
        return _outcome(SimDimension.AGENT_AVAILABILITY, 1.0, "no agents in scope",
                        {"n_agents": 0})
    excluded = set(assumptions.get("exclude_agents", []) or [])
    available = sum(1 for a in agents
                    if a.entity_id not in excluded and (a.state == "available" or a.approved))
    score = available / len(agents)
    return _outcome(SimDimension.AGENT_AVAILABILITY, score,
                    f"{available}/{len(agents)} agents available "
                    f"({len(excluded)} excluded by assumption)",
                    {"n_agents": len(agents), "available": available, "excluded": len(excluded)})


def _execution_structures(obs: Sequence, assumptions: dict) -> SimulationOutcome:
    execs = [o for o in obs if o.kind == "execution"]
    if not execs:
        return _outcome(SimDimension.EXECUTION_STRUCTURES, 1.0, "no executions in scope",
                        {"n_executions": 0})
    blocked = set(assumptions.get("blocked_executions", []) or [])
    ok = sum(1 for e in execs
             if e.entity_id not in blocked and e.approved
             and e.state not in ("blocked", "terminated"))
    score = ok / len(execs)
    return _outcome(SimDimension.EXECUTION_STRUCTURES, score,
                    f"{ok}/{len(execs)} executions structurally ready "
                    f"({len(blocked)} blocked by assumption)",
                    {"n_executions": len(execs), "ready": ok, "blocked": len(blocked)})


def _governance_controls(governance_summary: dict) -> SimulationOutcome:
    health = float(governance_summary.get("health_score", 1.0))
    n_violations = int(governance_summary.get("n_violations", 0))
    n_high_risks = int(governance_summary.get("n_high_risks", 0))
    score = health
    if n_violations:
        score = min(score, 0.49)
    return _outcome(SimDimension.GOVERNANCE_CONTROLS, score,
                    f"governance health={health}; {n_violations} violation(s); "
                    f"{n_high_risks} high risk(s)",
                    {"health_score": health, "n_violations": n_violations,
                     "n_high_risks": n_high_risks})


def evaluate(context: ScenarioContext) -> list:
    """Evaluate every effect dimension of a scenario context (deterministic)."""
    obs = observations_from_context(context)
    assumptions = context.assumptions_dict_parsed()
    return [
        _policy_effects(obs, assumptions),
        _constraint_effects(obs),
        _task_dependencies(obs),
        _agent_availability(obs, assumptions),
        _execution_structures(obs, assumptions),
        _governance_controls(context.governance_summary),
    ]
