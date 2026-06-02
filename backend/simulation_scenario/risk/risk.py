"""Simulation risk engine (V4-P9).

Derives **explainable** risk scores from a simulation's per-dimension outcomes across
six dimensions — execution, governance, policy, agent, dependency, and an aggregate
scenario risk. Each :class:`SimulationRiskRecord` carries a deterministic ``[0,1]``
score (``1 - dimension readiness``), a level, the factors behind it, and an
explanation. Reuses the V4-P7 risk-level thresholds for a consistent risk vocabulary.
"""

from __future__ import annotations

from typing import Sequence

from backend.governance_intelligence import risk_level_for  # shared risk vocabulary

from ..identity import mint_risk
from ..models.domain import SimulationRiskRecord, SimRiskDimension, SimDimension


def _risk(simulation_id: str, dimension: str, score: float, factors: list) -> SimulationRiskRecord:
    score = round(max(0.0, min(1.0, score)), 6)
    level = risk_level_for(score)
    return SimulationRiskRecord(
        risk_id=mint_risk(simulation_id, dimension), dimension=dimension, score=score,
        level=level, factors=tuple(factors),
        explanation=f"{dimension}: {level} (score={score}); " + "; ".join(factors))


def build_risks(simulation_id: str, outcomes: Sequence) -> list:
    """Generate the six explainable simulation-risk records from the outcomes."""
    by = {o.dimension: o for o in outcomes}

    def inv(dim: str) -> float:
        o = by.get(dim)
        return round(1.0 - (o.score if o else 1.0), 6)

    out = [
        _risk(simulation_id, SimRiskDimension.EXECUTION, inv(SimDimension.EXECUTION_STRUCTURES),
              [f"execution readiness={by.get(SimDimension.EXECUTION_STRUCTURES).score}"
               if SimDimension.EXECUTION_STRUCTURES in by else "no executions in scope"]),
        _risk(simulation_id, SimRiskDimension.GOVERNANCE, inv(SimDimension.GOVERNANCE_CONTROLS),
              [f"governance readiness={by.get(SimDimension.GOVERNANCE_CONTROLS).score}"
               if SimDimension.GOVERNANCE_CONTROLS in by else "no governance summary"]),
        _risk(simulation_id, SimRiskDimension.POLICY, inv(SimDimension.POLICY_EFFECTS),
              [f"policy coverage={by.get(SimDimension.POLICY_EFFECTS).score}"
               if SimDimension.POLICY_EFFECTS in by else "no policy data"]),
        _risk(simulation_id, SimRiskDimension.AGENT, inv(SimDimension.AGENT_AVAILABILITY),
              [f"agent availability={by.get(SimDimension.AGENT_AVAILABILITY).score}"
               if SimDimension.AGENT_AVAILABILITY in by else "no agents in scope"]),
        _risk(simulation_id, SimRiskDimension.DEPENDENCY, inv(SimDimension.TASK_DEPENDENCIES),
              [f"task dependency readiness={by.get(SimDimension.TASK_DEPENDENCIES).score}"
               if SimDimension.TASK_DEPENDENCIES in by else "no tasks in scope"]),
    ]
    overall = round(sum(o.score for o in outcomes) / (len(list(outcomes)) or 1), 6)
    out.append(_risk(simulation_id, SimRiskDimension.SCENARIO, round(1.0 - overall, 6),
                     [f"overall readiness across {len(list(outcomes))} dimensions={overall}"]))
    return out


def risk_summary(risks: Sequence) -> dict:
    risks = list(risks)
    by_level: dict = {}
    for r in risks:
        by_level[r.level] = by_level.get(r.level, 0) + 1
    overall = round(sum(r.score for r in risks) / (len(risks) or 1), 6)
    return {"n_risks": len(risks), "by_level": dict(sorted(by_level.items())),
            "overall_mean_score": overall,
            "n_high_or_critical": sum(1 for r in risks if r.level in ("high", "critical"))}
