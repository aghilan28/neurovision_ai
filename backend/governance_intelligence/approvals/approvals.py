"""Approval intelligence (V4-P7).

Analyzes the approval/authorization decisions of every governed entity (goal, plan,
task, agent approvals + execution authorizations) and derives per-entity
:class:`ApprovalRecord`s plus aggregate approval analytics: latency, backlog,
failures, throughput, and health.

All quantities are **deterministic and logical** — ``latency`` is the number of
governance events that preceded a terminal decision (never wall-clock). Approval
intelligence *observes* approvals; it never grants, denies, or modifies them.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_approval
from ..models.domain import ApprovalRecord
from ..models.observation import GovernedObservation


def build_approval(obs: GovernedObservation) -> ApprovalRecord:
    """Derive the approval-intelligence record for one observed entity."""
    return ApprovalRecord(
        approval_id=mint_approval(obs.kind, obs.entity_id), entity_kind=obs.kind,
        entity_id=obs.entity_id, approval_state=obs.approval_state, decision=obs.decision,
        authority=obs.authority, latency_steps=obs.latency_steps, approved=obs.approved,
        escalated=obs.escalated, policy_references=obs.policy_references,
        source_lineage_id=obs.lineage_id)


def build_approvals(observations: Sequence[GovernedObservation]) -> list[ApprovalRecord]:
    return [build_approval(o) for o in observations]


def approval_metrics(approvals: Sequence[ApprovalRecord]) -> dict:
    """Aggregate approval analytics (deterministic, logical units).

    * latency      — mean logical approval latency (governance events to decision).
    * backlog      — number of entities still pending / escalated (not yet approved).
    * failures     — number of denied/rejected approvals.
    * throughput   — number of approved/authorized entities.
    * health       — throughput / total, a [0,1] approval-health index.
    """
    approvals = list(approvals)
    total = len(approvals)
    approved = sum(1 for a in approvals if a.approved)
    failures = sum(1 for a in approvals if a.approval_state in ("rejected", "denied"))
    backlog = sum(1 for a in approvals if not a.approved
                  and a.approval_state not in ("rejected", "denied"))
    escalated = sum(1 for a in approvals if a.escalated)
    latencies = [a.latency_steps for a in approvals]
    mean_latency = round(sum(latencies) / total, 6) if total else 0.0
    max_latency = max(latencies) if latencies else 0
    health = round(approved / total, 6) if total else 1.0
    return {"n_approvals": total, "approved": approved, "failures": failures,
            "backlog": backlog, "escalated": escalated, "throughput": approved,
            "mean_latency_steps": mean_latency, "max_latency_steps": max_latency,
            "approval_health": health}


def approval_bottlenecks(approvals: Sequence[ApprovalRecord]) -> list[dict]:
    """Entities whose approval is a bottleneck (pending/escalated/denied), ordered."""
    out = []
    for a in approvals:
        if a.approved:
            continue
        out.append({"entity_kind": a.entity_kind, "entity_id": a.entity_id,
                    "approval_state": a.approval_state, "latency_steps": a.latency_steps})
    out.sort(key=lambda r: (-r["latency_steps"], r["entity_kind"], r["entity_id"]))
    return out
