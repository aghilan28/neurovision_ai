"""Shared builders for the V4-P9 / V4-P10 test suites.

Extends the V4-P7 fixture (`build_v4d`) with the Simulation & Scenario Layer (V4-P9),
all over the one shared platform lineage tracker. The simulation observes the governed
goals/policies/plans/tasks/agents/executions and the governance intelligence; its
lineage parents are those artifacts' nodes (plus the governance-intelligence node), so
``verify_chain`` from a simulation spans Patient -> ... -> Execution -> Governance
Intelligence -> Scenario -> Simulation. Not collected by pytest (no ``test_``).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v4d_helpers import build_v4d, active_policies, V4dFixture
from _v4c_helpers import goals, plans, tasks, agents, executions

from backend.simulation_scenario import SimulationScenarioService


@dataclass
class V4eFixture:
    base: V4dFixture
    tracker: object
    simulation: SimulationScenarioService


def build_simulation_service(base: V4dFixture) -> SimulationScenarioService:
    svc = SimulationScenarioService(lineage_tracker=base.tracker)
    svc.load_sources(
        goals=goals(base.base), policies=active_policies(base.base), plans=plans(base.base),
        tasks=tasks(base.base), agents=agents(base.base), executions=executions(base.base),
        governance_intelligence=base.intelligence)
    return svc


def build_v4e(n_cases: int = 2) -> V4eFixture:
    base = build_v4d(n_cases)
    return V4eFixture(base=base, tracker=base.tracker,
                      simulation=build_simulation_service(base))


def baseline(svc: SimulationScenarioService, scenario_type: str = "execution"):
    """A baseline scenario + its simulation (no assumptions)."""
    scenario = svc.create_scenario(scenario_type=scenario_type, name=f"{scenario_type}-baseline")
    return scenario, svc.simulate(scenario)
