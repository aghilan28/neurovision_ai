"""Task-layer lineage helpers built on ml.lineage.

Every task gets a content-addressed lineage node. A task's lineage parents are the
**ready plan** it derives from (and any task dependencies), so a task traces back
through the plan -> goal -> operational intelligence to the patient. Because every
task must derive from a ready plan, a task is never a lineage root.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    TASK_INTELLIGENCE_VERSION, TASK_DOMAIN_VERSION, TASK_IDENTITY_VERSION,
    TASK_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def task_version_bundle(**extra: object) -> dict:
    bundle = {
        "task_intelligence_version": TASK_INTELLIGENCE_VERSION,
        "task_domain_version": TASK_DOMAIN_VERSION,
        "task_identity_version": TASK_IDENTITY_VERSION,
        "task_lineage_version": TASK_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_task_lineage(task_id: str, *, parents: Sequence[str] = (), category: str = "",
                      reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                      extra: dict | None = None) -> LineageRecord:
    """A task lineage node parented by the ready plan (+ deps) it derives from."""
    outputs = {"task_id": task_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="task", versions=task_version_bundle(),
        inputs={"task_id": task_id, "category": category, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


def make_relationship_lineage(dependency_id: str, *, parents: Sequence[str] = (),
                              relation: str = "", created_at: str = DETERMINISTIC_EPOCH
                              ) -> LineageRecord:
    """A task-dependency lineage node parented by the related artifacts' nodes."""
    return make_lineage_record(
        kind="task_dependency", versions=task_version_bundle(),
        inputs={"dependency_id": dependency_id, "relation": relation},
        outputs={"dependency_id": dependency_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
