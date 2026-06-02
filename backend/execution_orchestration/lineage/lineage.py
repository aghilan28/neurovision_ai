"""Execution-layer lineage helpers built on ml.lineage.

Every execution gets a content-addressed lineage node. An execution's lineage
parents are the **approved agent assignment** it progresses (and, through it, the
agent + task), so an execution traces back through assignment -> agent/task -> plan
-> goal -> operational intelligence to the patient. Because every execution
references an approved assignment, an execution is never a lineage root.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    EXECUTION_ORCHESTRATION_VERSION, EXECUTION_DOMAIN_VERSION, EXECUTION_IDENTITY_VERSION,
    EXECUTION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def execution_version_bundle(**extra: object) -> dict:
    bundle = {
        "execution_orchestration_version": EXECUTION_ORCHESTRATION_VERSION,
        "execution_domain_version": EXECUTION_DOMAIN_VERSION,
        "execution_identity_version": EXECUTION_IDENTITY_VERSION,
        "execution_lineage_version": EXECUTION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_execution_lineage(execution_id: str, *, parents: Sequence[str] = (),
                           reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                           extra: dict | None = None) -> LineageRecord:
    """An execution lineage node parented by the assignment/agent/task it progresses."""
    outputs = {"execution_id": execution_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="execution", versions=execution_version_bundle(),
        inputs={"execution_id": execution_id, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


def make_relationship_lineage(relationship_id: str, *, parents: Sequence[str] = (),
                              relation: str = "", created_at: str = DETERMINISTIC_EPOCH
                              ) -> LineageRecord:
    """An execution-relationship lineage node parented by the related artifacts' nodes."""
    return make_lineage_record(
        kind="execution_relationship", versions=execution_version_bundle(),
        inputs={"relationship_id": relationship_id, "relation": relation},
        outputs={"relationship_id": relationship_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
