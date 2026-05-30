"""Governance risk engine (V4-P7).

Generates **explainable** governance-risk scores across six dimensions — approval,
execution, policy, constraint, assignment, and governance — for the observed
entities. Each :class:`GovernanceRiskRecord` carries a deterministic [0,1] score, a
derived level, the human-readable factors that produced it, and a one-line
explanation. The engine is observation-only; it never changes governance.

Scoring is a pure function of the observed governance state (no wall-clock, no
randomness), so the same platform state always yields identical scores.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_risk
from ..models.domain import (
    GovernanceRiskRecord, RiskDimension, risk_level_for, GovernedKind,
)
from ..models.observation import GovernedObservation


def _record(obs: GovernedObservation, dimension: str, score: float,
            factors: Sequence[str]) -> GovernanceRiskRecord:
    score = round(max(0.0, min(1.0, score)), 6)
    level = risk_level_for(score)
    factors = tuple(factors)
    explanation = (f"{dimension} for {obs.kind} {obs.entity_id}: {level} "
                   f"(score={score}); " + "; ".join(factors) if factors
                   else f"{dimension}: {level} (score={score})")
    return GovernanceRiskRecord(
        risk_id=mint_risk(dimension, obs.kind, obs.entity_id), dimension=dimension,
        entity_kind=obs.kind, entity_id=obs.entity_id, score=score, level=level,
        factors=factors, explanation=explanation, source_lineage_id=obs.lineage_id)


def _approval_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    if obs.denied:
        score, factors = 0.9, ["approval/authorization refused"]
    elif obs.escalated:
        score, factors = 0.6, ["approval escalated, awaiting resolution"]
    elif obs.pending:
        score, factors = 0.5, ["approval still pending"]
    elif obs.approved:
        score, factors = 0.0, ["approved/authorized by governance"]
    else:
        score, factors = 0.3, [f"approval_state={obs.approval_state}"]
    return _record(obs, RiskDimension.APPROVAL, score, factors)


def _governance_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    score, factors = 0.0, []
    if obs.live and not obs.approved:
        score += 0.6
        factors.append("live without governance approval")
    if obs.escalation_required or obs.escalated:
        score += 0.3
        factors.append("escalation flagged")
    if not obs.policy_references and obs.kind not in (GovernedKind.POLICY, GovernedKind.CONSTRAINT):
        score += 0.2
        factors.append("no policy reference")
    if not factors:
        factors = ["fully governed; approved with policy references"]
    return _record(obs, RiskDimension.GOVERNANCE, score, factors)


def _policy_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    if obs.policy_references:
        return _record(obs, RiskDimension.POLICY, 0.0,
                       [f"{len(obs.policy_references)} policy reference(s)"])
    return _record(obs, RiskDimension.POLICY, 0.5, ["no governing policy referenced"])


def _constraint_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    # constraint risk is low when the entity is approved (its constraints were checked).
    score = 0.0 if obs.approved else 0.4
    factors = (["constraints satisfied at approval"] if obs.approved
               else ["constraints not yet confirmed (not approved)"])
    return _record(obs, RiskDimension.CONSTRAINT, score, factors)


def _execution_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    state_score = {"completed": 0.0, "active": 0.2, "queued": 0.2, "authorized": 0.2,
                   "paused": 0.5, "blocked": 0.7, "terminated": 0.8, "proposed": 0.3}
    score = state_score.get(obs.state, 0.3)
    factors = [f"execution state={obs.state}"]
    if not obs.approved:
        score = max(score, 0.6)
        factors.append("not authorized")
    return _record(obs, RiskDimension.EXECUTION, score, factors)


def _assignment_risk(obs: GovernedObservation) -> GovernanceRiskRecord:
    score = 0.0 if obs.approved else 0.5
    factors = (["assignment governed by an approved participant"] if obs.approved
               else ["participant/execution not approved for assignment"])
    return _record(obs, RiskDimension.ASSIGNMENT, score, factors)


def build_risks(observations: Sequence[GovernedObservation]) -> list[GovernanceRiskRecord]:
    """Generate every applicable governance-risk record across the six dimensions."""
    out: list[GovernanceRiskRecord] = []
    for obs in observations:
        out.append(_approval_risk(obs))
        out.append(_governance_risk(obs))
        out.append(_policy_risk(obs))
        out.append(_constraint_risk(obs))
        if obs.kind == GovernedKind.EXECUTION:
            out.append(_execution_risk(obs))
        if obs.kind in (GovernedKind.AGENT, GovernedKind.EXECUTION):
            out.append(_assignment_risk(obs))
    return out


def risk_summary(risks: Sequence[GovernanceRiskRecord]) -> dict:
    risks = list(risks)
    by_dimension: dict = {}
    by_level: dict = {}
    for r in risks:
        by_dimension.setdefault(r.dimension, []).append(r.score)
        by_level[r.level] = by_level.get(r.level, 0) + 1
    dimension_mean = {d: round(sum(v) / len(v), 6) for d, v in sorted(by_dimension.items())}
    overall = round(sum(r.score for r in risks) / len(risks), 6) if risks else 0.0
    return {"n_risks": len(risks), "by_dimension_mean": dimension_mean,
            "by_level": dict(sorted(by_level.items())), "overall_mean_score": overall,
            "n_high_or_critical": sum(1 for r in risks if r.level in ("high", "critical"))}


def highest_risks(risks: Sequence[GovernanceRiskRecord], limit: int = 10) -> list[dict]:
    ordered = sorted(risks, key=lambda r: (-r.score, r.dimension, r.entity_id))
    return [r.to_dict() for r in ordered[:limit]]
