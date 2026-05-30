"""Comparison engine (V4-P9).

Compares two or more simulated scenarios (A / B / C / …) and produces a deterministic
:class:`ComparisonRecord`: per-scenario advantages, risks, the tradeoffs between them,
the governance impact, the constraint impact, and a recommended scenario (highest
readiness, then lowest risk, with a stable id tie-break). Comparison observes and
ranks; it never executes the recommendation.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_comparison
from ..models.domain import ComparisonRecord, SimDimension
from ..risk import risk_summary


def _dim_score(simulation, dimension: str) -> float:
    for o in simulation.result.outcomes:
        if o.dimension == dimension:
            return o.score
    return 1.0


def build_comparison(pairs: Sequence) -> ComparisonRecord:
    """Compare a sequence of (ScenarioRecord, SimulationRecord) pairs (>= 2 required)."""
    pairs = list(pairs)
    if len(pairs) < 2:
        raise ValueError("comparison requires at least two scenarios")

    rows = []
    for scenario, simulation in pairs:
        rs = risk_summary(simulation.risks)
        rows.append({
            "scenario_id": scenario.scenario_id, "name": scenario.name,
            "scenario_type": scenario.scenario_type,
            "simulation_id": simulation.simulation_id,
            "readiness": simulation.result.readiness_score,
            "readiness_status": simulation.result.readiness_status,
            "risk": rs["overall_mean_score"], "n_high_or_critical": rs["n_high_or_critical"],
            "governance_impact": _dim_score(simulation, SimDimension.GOVERNANCE_CONTROLS),
            "constraint_impact": _dim_score(simulation, SimDimension.CONSTRAINT_EFFECTS),
        })

    best_readiness = max(r["readiness"] for r in rows)
    least_risk = min(r["risk"] for r in rows)
    advantages = tuple(
        {"scenario_id": r["scenario_id"], "advantages":
         ([f"highest readiness ({r['readiness']})"] if r["readiness"] == best_readiness else [])
         + ([f"lowest risk ({r['risk']})"] if r["risk"] == least_risk else [])}
        for r in rows)
    risks = tuple({"scenario_id": r["scenario_id"], "risk": r["risk"],
                   "n_high_or_critical": r["n_high_or_critical"]} for r in rows)

    ordered = sorted(rows, key=lambda r: (-r["readiness"], r["risk"], r["scenario_id"]))
    recommended = ordered[0]["scenario_id"]

    tradeoffs = []
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        tradeoffs.append(
            f"{a['name']} > {b['name']}: readiness {a['readiness']} vs {b['readiness']}, "
            f"risk {a['risk']} vs {b['risk']}")

    governance_impact = {r["scenario_id"]: r["governance_impact"] for r in rows}
    constraint_impact = {r["scenario_id"]: r["constraint_impact"] for r in rows}

    scenario_ids = tuple(r["scenario_id"] for r in rows)
    simulation_ids = tuple(r["simulation_id"] for r in rows)
    from ml.provenance import hash_obj
    signature = hash_obj({"rows": rows, "recommended": recommended})
    comparison_id = mint_comparison(scenario_ids, signature)

    return ComparisonRecord(
        comparison_id=comparison_id, scenario_ids=scenario_ids, simulation_ids=simulation_ids,
        advantages=advantages, risks=risks, tradeoffs=tuple(tradeoffs),
        governance_impact=governance_impact, constraint_impact=constraint_impact,
        recommended_scenario_id=recommended,
        explanation=(f"recommended {recommended} by highest readiness then lowest risk "
                     f"across {len(rows)} scenarios"))
