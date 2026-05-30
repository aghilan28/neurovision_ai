"""Simulation engine (V4-P9).

Runs a scenario deterministically: evaluates every effect dimension, then derives the
forecasts and simulation risks, and assembles a :class:`SimulationResult` with an
overall readiness score/status. **No randomness, no execution, no state mutation** —
the same scenario always produces the same result.
"""

from __future__ import annotations

from ..identity import mint_simulation
from ..models.domain import SimulationResult, OutcomeStatus, ScenarioRecord
from ..evaluation import evaluate
from ..forecast import build_forecasts
from ..risk import build_risks


def _readiness_status(score: float) -> str:
    if score >= 0.8:
        return OutcomeStatus.READY
    if score >= 0.5:
        return OutcomeStatus.DEGRADED
    return OutcomeStatus.BLOCKED


def run_simulation(scenario: ScenarioRecord) -> tuple[str, SimulationResult]:
    """Deterministically evaluate a scenario into a (simulation_id, result) pair."""
    simulation_id = mint_simulation(scenario.scenario_id, scenario.context.signature())
    outcomes = tuple(evaluate(scenario.context))
    forecasts = tuple(build_forecasts(simulation_id, outcomes, scenario.context.governance_summary))
    risks = tuple(build_risks(simulation_id, outcomes))

    readiness = round(sum(o.score for o in outcomes) / (len(outcomes) or 1), 6)
    status = _readiness_status(readiness)
    blocked = [o.dimension for o in outcomes if o.status == OutcomeStatus.BLOCKED]
    summary = (f"scenario '{scenario.name}' ({scenario.scenario_type}): readiness={readiness} "
               f"({status})" + (f"; blocked: {', '.join(blocked)}" if blocked else ""))
    result = SimulationResult(outcomes=outcomes, forecasts=forecasts, risks=risks,
                              readiness_score=readiness, readiness_status=status, summary=summary)
    return simulation_id, result
