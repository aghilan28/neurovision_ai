"""Violation intelligence (V4-P7).

Detects governance violations from the observed governed entities and produces
:class:`ViolationRecord`s with a severity level and an impact analysis. Detection is
**deterministic and observation-only** — it never enforces, blocks, or modifies
governance; it surfaces conditions a human must review.

Detected violation types (none of which should occur on a correctly-governed
platform — a non-empty result is a signal for human oversight):

  * ``lifecycle_violation``     — an entity is in a *live* lifecycle state but its
                                  governance is not approved/authorized.
  * ``approval_violation``      — a non-execution entity was rejected by governance.
  * ``authorization_violation`` — an execution authorization was denied.
  * ``governance_violation``    — an entity is escalated/flagged for governance.
  * ``policy_violation``        — a live, governed entity carries no policy reference.
  * ``constraint_violation``    — (reserved) a constraint reference is unsatisfied.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_violation
from ..models.domain import ViolationRecord, ViolationType, Severity, GovernedKind
from ..models.observation import GovernedObservation

# impact text per violation type (deterministic).
_IMPACT: dict[str, str] = {
    ViolationType.LIFECYCLE: "entity advanced past governance without approval",
    ViolationType.APPROVAL: "approval was refused; entity must not proceed",
    ViolationType.AUTHORIZATION: "execution authorization refused; execution must not run",
    ViolationType.GOVERNANCE: "entity requires governance escalation / human review",
    ViolationType.POLICY: "no policy governs a live entity (ungoverned progression)",
    ViolationType.CONSTRAINT: "a referenced constraint is unsatisfied",
}


def _violation(obs: GovernedObservation, vtype: str, severity: str, detail: str) -> ViolationRecord:
    return ViolationRecord(
        violation_id=mint_violation(obs.kind, obs.entity_id, vtype), entity_kind=obs.kind,
        entity_id=obs.entity_id, violation_type=vtype, severity=severity, detail=detail,
        impact=_IMPACT.get(vtype, ""), source_lineage_id=obs.lineage_id)


def detect_violations(observations: Sequence[GovernedObservation]) -> list[ViolationRecord]:
    """Return every detected governance violation (empty on a clean platform)."""
    out: list[ViolationRecord] = []
    for obs in observations:
        # lifecycle: live but not approved/authorized
        if obs.live and not obs.approved:
            out.append(_violation(obs, ViolationType.LIFECYCLE, Severity.CRITICAL,
                                   f"state={obs.state} approval_state={obs.approval_state}"))
        # approval / authorization refused
        if obs.denied:
            if obs.kind == GovernedKind.EXECUTION:
                out.append(_violation(obs, ViolationType.AUTHORIZATION, Severity.HIGH,
                                      f"authorization_state={obs.approval_state}"))
            else:
                out.append(_violation(obs, ViolationType.APPROVAL, Severity.HIGH,
                                      f"approval_state={obs.approval_state}"))
        # governance escalation flagged
        if obs.escalated or obs.escalation_required:
            out.append(_violation(obs, ViolationType.GOVERNANCE, Severity.MODERATE,
                                   "escalation required / governance flagged"))
        # policy coverage: a live, governed entity should reference a policy
        if obs.live and obs.approved and not obs.policy_references \
                and obs.kind not in (GovernedKind.POLICY, GovernedKind.CONSTRAINT):
            out.append(_violation(obs, ViolationType.POLICY, Severity.LOW,
                                   "live entity has no policy reference"))
    return out


def violation_summary(violations: Sequence[ViolationRecord]) -> dict:
    by_type: dict = {}
    by_severity: dict = {}
    for v in violations:
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
    n_critical = by_severity.get(Severity.CRITICAL, 0) + by_severity.get(Severity.HIGH, 0)
    return {"n_violations": len(list(violations)), "by_type": dict(sorted(by_type.items())),
            "by_severity": dict(sorted(by_severity.items())),
            "n_high_or_critical": n_critical, "clean": len(list(violations)) == 0}
