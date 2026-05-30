"""Governance analytics (V4-P7).

Aggregates the derived approval / violation / escalation / risk intelligence into
governance **metrics**, **trends**, an overall governance **health score**, and the
governance **bottlenecks** that need human attention. Everything is a deterministic
projection of the observed governance state — analytics adds no new truth and never
modifies governance.
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import GovernanceMetric
from ..models.observation import GovernedObservation
from ..approvals import approval_metrics, approval_bottlenecks
from ..violations import violation_summary
from ..escalations import escalation_summary
from ..risk import risk_summary, highest_risks


def governance_health(approvals, violations, escalations, risks) -> float:
    """A composite [0,1] governance-health score (deterministic).

    health = approval_health * (1 - violation_penalty) * (1 - risk_penalty), where
    the penalties are bounded by the share of high/critical findings.
    """
    am = approval_metrics(approvals)
    vm = violation_summary(violations)
    rm = risk_summary(risks)
    n_entities = max(1, am["n_approvals"])
    violation_penalty = min(1.0, vm["n_high_or_critical"] / n_entities)
    risk_penalty = min(1.0, rm["n_high_or_critical"] / max(1, rm["n_risks"]))
    health = am["approval_health"] * (1.0 - violation_penalty) * (1.0 - risk_penalty)
    return round(health, 6)


def build_metrics(observations: Sequence[GovernedObservation], approvals, violations,
                  escalations, risks) -> list[GovernanceMetric]:
    """Build the governance analytics metric set (deterministic)."""
    am = approval_metrics(approvals)
    vm = violation_summary(violations)
    em = escalation_summary(escalations)
    rm = risk_summary(risks)
    health = governance_health(approvals, violations, escalations, risks)
    metrics = [
        GovernanceMetric("n_observed", float(len(list(observations))), "entities",
                         "governed entities observed"),
        GovernanceMetric("approval_health", am["approval_health"], "ratio",
                         "approved / total"),
        GovernanceMetric("approval_throughput", float(am["throughput"]), "entities",
                         "approved/authorized entities"),
        GovernanceMetric("approval_backlog", float(am["backlog"]), "entities",
                         "pending/escalated entities"),
        GovernanceMetric("mean_approval_latency", am["mean_latency_steps"], "steps",
                         "mean logical approval latency"),
        GovernanceMetric("n_violations", float(vm["n_violations"]), "violations",
                         "detected governance violations"),
        GovernanceMetric("n_high_or_critical_violations", float(vm["n_high_or_critical"]),
                         "violations", "high/critical violations"),
        GovernanceMetric("escalation_effectiveness", em["effectiveness"], "ratio",
                         "resolved / requested escalations"),
        GovernanceMetric("overall_risk", rm["overall_mean_score"], "score",
                         "mean governance risk score"),
        GovernanceMetric("n_high_or_critical_risks", float(rm["n_high_or_critical"]), "risks",
                         "high/critical risk findings"),
        GovernanceMetric("governance_health", health, "score",
                         "composite governance health"),
    ]
    return metrics


def governance_trends(observations: Sequence[GovernedObservation]) -> dict:
    """Approval rate per governed kind (a deterministic distribution 'trend')."""
    by_kind: dict = {}
    for o in observations:
        bucket = by_kind.setdefault(o.kind, {"total": 0, "approved": 0})
        bucket["total"] += 1
        if o.approved:
            bucket["approved"] += 1
    trends = {}
    for kind, b in sorted(by_kind.items()):
        trends[kind] = {"total": b["total"], "approved": b["approved"],
                        "approval_rate": round(b["approved"] / b["total"], 6) if b["total"] else 1.0}
    return trends


def governance_bottlenecks(approvals, risks) -> dict:
    """The governance bottlenecks needing attention: stuck approvals + highest risks."""
    return {"approval_bottlenecks": approval_bottlenecks(approvals),
            "highest_risks": highest_risks(risks, limit=10)}
