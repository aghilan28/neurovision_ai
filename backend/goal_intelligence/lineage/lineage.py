"""Goal-layer lineage helpers built on ml.lineage.

Every goal gets a content-addressed lineage node. A goal's lineage parents are the
upstream artifacts it is *derived from* — the analytics/recommendation/workflow
nodes that motivated the intent (when supplied) — so a goal traces back through the
operational intelligence to the patient. A goal with no upstream motivation is a
root intent (e.g. a strategic goal authored directly) and parents the platform
governance origin only if provided.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    GOAL_INTELLIGENCE_VERSION, GOAL_DOMAIN_VERSION, GOAL_IDENTITY_VERSION,
    GOAL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def goal_version_bundle(**extra: object) -> dict:
    bundle = {
        "goal_intelligence_version": GOAL_INTELLIGENCE_VERSION,
        "goal_domain_version": GOAL_DOMAIN_VERSION,
        "goal_identity_version": GOAL_IDENTITY_VERSION,
        "goal_lineage_version": GOAL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_goal_lineage(goal_id: str, *, parents: Sequence[str] = (), category: str = "",
                      reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                      extra: dict | None = None) -> LineageRecord:
    """A goal lineage node parented by the upstream artifacts it derives from."""
    outputs = {"goal_id": goal_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="goal", versions=goal_version_bundle(),
        inputs={"goal_id": goal_id, "category": category, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


def make_relationship_lineage(relationship_id: str, *, parents: Sequence[str] = (),
                              relation: str = "", created_at: str = DETERMINISTIC_EPOCH
                              ) -> LineageRecord:
    """A goal-relationship lineage node parented by the related artifacts' nodes."""
    return make_lineage_record(
        kind="goal_relationship", versions=goal_version_bundle(),
        inputs={"relationship_id": relationship_id, "relation": relation},
        outputs={"relationship_id": relationship_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
