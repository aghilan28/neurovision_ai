"""Forecast layer (V4-P9).

Projects explainable outcomes from a simulation's per-dimension outcomes: execution,
risk, governance, approval, and constraint forecasts. Each :class:`ForecastRecord`
carries a deterministic projected status, a derived (never random) confidence in
``[0,1]``, the factors behind it, and a plain-language explanation. Forecasts are
projections of the observed state — they describe what *would* happen; they never make
it happen.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_forecast
from ..models.domain import (
    ForecastRecord, ForecastType, SimDimension,
)


def _by_dim(outcomes: Sequence) -> dict:
    return {o.dimension: o for o in outcomes}


def _proj_status(score: float, ready: str, degraded: str, blocked: str) -> str:
    if score >= 0.8:
        return ready
    if score >= 0.5:
        return degraded
    return blocked


def _forecast(simulation_id: str, ftype: str, status: str, confidence: float,
              factors: list, explanation: str) -> ForecastRecord:
    return ForecastRecord(
        forecast_id=mint_forecast(simulation_id, ftype), forecast_type=ftype,
        projected_status=status, confidence=round(max(0.0, min(1.0, confidence)), 6),
        factors=tuple(factors), explanation=explanation)


def build_forecasts(simulation_id: str, outcomes: Sequence,
                    governance_summary: dict | None = None) -> list:
    """Build the five explainable forecasts from a simulation's outcomes."""
    by = _by_dim(outcomes)
    governance_summary = governance_summary or {}

    def score(dim: str) -> float:
        o = by.get(dim)
        return o.score if o else 1.0

    exec_conf = min(score(SimDimension.EXECUTION_STRUCTURES),
                    score(SimDimension.TASK_DEPENDENCIES),
                    score(SimDimension.AGENT_AVAILABILITY))
    execution = _forecast(
        simulation_id, ForecastType.EXECUTION,
        _proj_status(exec_conf, "would_complete", "would_complete_degraded", "would_block"),
        exec_conf,
        [f"execution_structures={score(SimDimension.EXECUTION_STRUCTURES)}",
         f"task_dependencies={score(SimDimension.TASK_DEPENDENCIES)}",
         f"agent_availability={score(SimDimension.AGENT_AVAILABILITY)}"],
        "execution readiness = min(execution structures, task dependencies, agent availability)")

    overall = round(sum(o.score for o in outcomes) / (len(list(outcomes)) or 1), 6)
    risk_score = round(1.0 - overall, 6)
    risk = _forecast(
        simulation_id, ForecastType.RISK,
        _proj_status(overall, "low_risk", "moderate_risk", "high_risk"), overall,
        [f"overall_readiness={overall}", f"residual_risk={risk_score}"],
        "risk forecast = 1 - mean(dimension readiness); confidence = overall readiness")

    gov_score = score(SimDimension.GOVERNANCE_CONTROLS)
    governance = _forecast(
        simulation_id, ForecastType.GOVERNANCE,
        _proj_status(gov_score, "controls_hold", "controls_strained", "controls_fail"), gov_score,
        [f"governance_controls={gov_score}",
         f"n_violations={governance_summary.get('n_violations', 0)}"],
        "governance forecast tracks the governance-controls readiness + violation count")

    appr_score = score(SimDimension.CONSTRAINT_EFFECTS)
    approval = _forecast(
        simulation_id, ForecastType.APPROVAL,
        _proj_status(appr_score, "would_approve", "approval_at_risk", "would_reject"), appr_score,
        [f"approved_fraction={appr_score}"],
        "approval forecast = fraction of in-scope entities already governance-approved")

    con_score = score(SimDimension.CONSTRAINT_EFFECTS)
    constraint = _forecast(
        simulation_id, ForecastType.CONSTRAINT,
        _proj_status(con_score, "constraints_hold", "constraints_strained", "constraints_violated"),
        con_score, [f"constraint_satisfaction={con_score}"],
        "constraint forecast = fraction of in-scope entities satisfying their constraints")

    return [execution, risk, governance, approval, constraint]


def forecast_summary(forecasts: Sequence) -> dict:
    return {"n_forecasts": len(list(forecasts)),
            "by_type": {f.forecast_type: f.projected_status for f in forecasts},
            "mean_confidence": round(
                sum(f.confidence for f in forecasts) / (len(list(forecasts)) or 1), 6)}
