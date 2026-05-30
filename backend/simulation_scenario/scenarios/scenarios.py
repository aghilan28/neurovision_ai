"""Scenario engine (V4-P9).

Builds reproducible scenarios of each supported type — goal, plan, task, agent,
execution, governance, and risk — over a :class:`SimulationView`. A scenario is a
*hypothesis*: a frozen, content-addressed snapshot of the observed artifacts plus
declarative what-if assumptions. The same view + type + name + assumptions always
produces the same ``scenario_id`` (reproducible). The scenario engine does not run the
simulation (the simulation engine does) and never touches production state.
"""

from __future__ import annotations

from ..identity import mint_scenario
from ..models.domain import ScenarioRecord, SCENARIO_TYPES
from ..models.context import SimulationView, build_context


def build_scenario(view: SimulationView, *, scenario_type: str, name: str,
                   description: str = "", assumptions: dict | None = None) -> ScenarioRecord:
    """Build a reproducible (pre-finalize) scenario record of ``scenario_type``."""
    if scenario_type not in SCENARIO_TYPES:
        raise ValueError(f"unknown scenario_type {scenario_type!r}; valid: {sorted(SCENARIO_TYPES)}")
    context = build_context(view, focus_kind=scenario_type, assumptions=assumptions)
    ident = mint_scenario(scenario_type, name, context.signature())
    return ScenarioRecord(scenario_id=ident.id, scenario_type=scenario_type, name=name,
                          context=context, description=description)


def goal_scenario(view, name="goal-scenario", **kw):
    return build_scenario(view, scenario_type="goal", name=name, **kw)


def plan_scenario(view, name="plan-scenario", **kw):
    return build_scenario(view, scenario_type="plan", name=name, **kw)


def task_scenario(view, name="task-scenario", **kw):
    return build_scenario(view, scenario_type="task", name=name, **kw)


def agent_scenario(view, name="agent-scenario", **kw):
    return build_scenario(view, scenario_type="agent", name=name, **kw)


def execution_scenario(view, name="execution-scenario", **kw):
    return build_scenario(view, scenario_type="execution", name=name, **kw)


def governance_scenario(view, name="governance-scenario", **kw):
    return build_scenario(view, scenario_type="governance", name=name, **kw)


def risk_scenario(view, name="risk-scenario", **kw):
    return build_scenario(view, scenario_type="risk", name=name, **kw)
