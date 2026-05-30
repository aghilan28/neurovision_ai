"""Governance monitoring (V4-P7).

Answers the human-oversight questions the platform could not previously answer:

  * *Which executions require intervention?*
  * *What operational state requires human review?*

These are **read-only** projections over the observed governance state and the
derived violation/escalation/risk intelligence. Monitoring flags conditions for a
human; it never intervenes, suspends, or modifies anything (intervention is a
governed backend act, surfaced — but never performed — by the workstation).
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import GovernedKind, RiskLevel, Severity
from ..models.observation import GovernedObservation


def executions_requiring_intervention(observations: Sequence[GovernedObservation],
                                      risks: Sequence = ()) -> list[dict]:
    """Executions whose observed state needs human intervention.

    An execution needs intervention when it is paused, blocked, terminated, escalated,
    or not authorized while live.
    """
    flagged = []
    risk_by_entity = {(r.entity_kind, r.entity_id): r for r in risks
                      if getattr(r, "dimension", "") == "execution_risk"}
    for o in observations:
        if o.kind != GovernedKind.EXECUTION:
            continue
        reasons = []
        if o.state in ("paused", "blocked", "terminated"):
            reasons.append(f"state={o.state}")
        if o.escalated or o.escalation_required:
            reasons.append("escalation flagged")
        if o.live and not o.approved:
            reasons.append("active without authorization")
        if reasons:
            risk = risk_by_entity.get((o.kind, o.entity_id))
            flagged.append({"entity_kind": o.kind, "entity_id": o.entity_id, "state": o.state,
                            "reasons": reasons,
                            "risk_level": risk.level if risk else RiskLevel.MODERATE})
    return flagged


def state_requiring_review(observations: Sequence[GovernedObservation], violations: Sequence = (),
                           escalations: Sequence = ()) -> list[dict]:
    """Any operational state requiring human review (violations/escalations/stuck approvals)."""
    out: list[dict] = []
    for v in violations:
        if v.severity in (Severity.HIGH, Severity.CRITICAL, Severity.MODERATE):
            out.append({"reason": "violation", "type": v.violation_type, "severity": v.severity,
                        "entity_kind": v.entity_kind, "entity_id": v.entity_id})
    for e in escalations:
        if not e.effective:
            out.append({"reason": "unresolved_escalation", "outcome": e.outcome,
                        "entity_kind": e.entity_kind, "entity_id": e.entity_id})
    for o in observations:
        if o.pending or (o.live and not o.approved):
            out.append({"reason": "pending_approval", "entity_kind": o.kind,
                        "entity_id": o.entity_id, "approval_state": o.approval_state})
    return out


def monitoring_summary(observations: Sequence[GovernedObservation], violations: Sequence = (),
                       escalations: Sequence = (), risks: Sequence = ()) -> dict:
    intervene = executions_requiring_intervention(observations, risks)
    review = state_requiring_review(observations, violations, escalations)
    return {"n_executions_requiring_intervention": len(intervene),
            "executions_requiring_intervention": intervene,
            "n_states_requiring_review": len(review), "states_requiring_review": review,
            "clear": not intervene and not review}
