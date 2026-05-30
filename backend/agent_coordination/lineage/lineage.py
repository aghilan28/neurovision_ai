"""Agent-layer lineage helpers built on ml.lineage.

Every agent gets a content-addressed lineage node. An agent's lineage parents are
the governing artifacts it derives from (the goals/policies/plans that motivated it,
when supplied); a root participant authored directly may have no upstream parent. An
**assignment** lineage node parents both the agent node and the assigned work unit's
node (e.g. the task being assigned) — so an assignment traces to the task and,
through it, back to the patient.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    AGENT_COORDINATION_VERSION, AGENT_DOMAIN_VERSION, AGENT_IDENTITY_VERSION,
    AGENT_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def agent_version_bundle(**extra: object) -> dict:
    bundle = {
        "agent_coordination_version": AGENT_COORDINATION_VERSION,
        "agent_domain_version": AGENT_DOMAIN_VERSION,
        "agent_identity_version": AGENT_IDENTITY_VERSION,
        "agent_lineage_version": AGENT_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_agent_lineage(agent_id: str, *, parents: Sequence[str] = (), category: str = "",
                       reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                       extra: dict | None = None) -> LineageRecord:
    """An agent lineage node parented by the governing artifacts it derives from."""
    outputs = {"agent_id": agent_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="agent", versions=agent_version_bundle(),
        inputs={"agent_id": agent_id, "category": category, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


def make_assignment_lineage(assignment_id: str, *, parents: Sequence[str] = (),
                            target_kind: str = "", created_at: str = DETERMINISTIC_EPOCH
                            ) -> LineageRecord:
    """An assignment lineage node parented by the agent node + the work-unit node."""
    return make_lineage_record(
        kind="agent_assignment", versions=agent_version_bundle(),
        inputs={"assignment_id": assignment_id, "target_kind": target_kind},
        outputs={"assignment_id": assignment_id},
        parents=tuple(p for p in parents if p), created_at=created_at)


def make_relationship_lineage(relationship_id: str, *, parents: Sequence[str] = (),
                              relation: str = "", created_at: str = DETERMINISTIC_EPOCH
                              ) -> LineageRecord:
    """An agent-relationship lineage node parented by the related artifacts' nodes."""
    return make_lineage_record(
        kind="agent_relationship", versions=agent_version_bundle(),
        inputs={"relationship_id": relationship_id, "relation": relation},
        outputs={"relationship_id": relationship_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
