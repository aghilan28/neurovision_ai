"""Escalation intelligence (V4-P7).

Analyzes governance escalations across the observed entities and derives
:class:`EscalationRecord`s: which entities requested escalation, the outcome,
the (logical) delay, the escalation risk, and whether the escalation was effective.

Escalation intelligence *observes*; it never raises, resolves, or routes an
escalation. Delays are deterministic and logical (governance events between the
escalation request and the terminal decision), never wall-clock.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_escalation
from ..models.domain import EscalationRecord, RiskLevel
from ..models.observation import GovernedObservation


def _escalation_delay(obs: GovernedObservation) -> int:
    """Logical delay: governance events recorded after the escalation request."""
    seen = False
    delay = 0
    for ev in obs.history:
        if seen:
            delay += 1
        if ev.get("decision") == "escalated":
            seen = True
    return delay


def build_escalation(obs: GovernedObservation) -> EscalationRecord:
    requested = obs.escalated or obs.escalation_required
    delay = _escalation_delay(obs)
    if not requested:
        outcome = "none"
    elif obs.approved:
        outcome = "resolved"
    elif obs.denied:
        outcome = "unresolved"
    else:
        outcome = "pending"
    effective = outcome == "resolved"
    if not requested:
        risk = RiskLevel.LOW
    elif effective:
        risk = RiskLevel.MODERATE
    elif outcome == "pending":
        risk = RiskLevel.HIGH
    else:
        risk = RiskLevel.CRITICAL
    return EscalationRecord(
        escalation_id=mint_escalation(obs.kind, obs.entity_id), entity_kind=obs.kind,
        entity_id=obs.entity_id, requested=requested, outcome=outcome, delay_steps=delay,
        risk=risk, effective=effective, source_lineage_id=obs.lineage_id)


def build_escalations(observations: Sequence[GovernedObservation]) -> list[EscalationRecord]:
    """Build escalation records for entities that requested escalation."""
    return [build_escalation(o) for o in observations if (o.escalated or o.escalation_required)]


def escalation_summary(escalations: Sequence[EscalationRecord]) -> dict:
    escalations = list(escalations)
    by_outcome: dict = {}
    for e in escalations:
        by_outcome[e.outcome] = by_outcome.get(e.outcome, 0) + 1
    resolved = by_outcome.get("resolved", 0)
    total = len(escalations)
    effectiveness = round(resolved / total, 6) if total else 1.0
    mean_delay = round(sum(e.delay_steps for e in escalations) / total, 6) if total else 0.0
    return {"n_escalations": total, "by_outcome": dict(sorted(by_outcome.items())),
            "resolved": resolved, "effectiveness": effectiveness,
            "mean_delay_steps": mean_delay,
            "n_unresolved": sum(1 for e in escalations if not e.effective)}
