"""Plan-layer lineage helpers built on ml.lineage.

Every plan gets a content-addressed lineage node. A plan's lineage parents are the
**approved goal** it derives from (and any plan dependencies), so a plan traces back
through the goal — and the operational intelligence the goal derived from — to the
patient. Because every plan must derive from an approved goal, a plan is never a
lineage root.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    PLANNING_FOUNDATION_VERSION, PLAN_DOMAIN_VERSION, PLAN_IDENTITY_VERSION,
    PLAN_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def plan_version_bundle(**extra: object) -> dict:
    bundle = {
        "planning_foundation_version": PLANNING_FOUNDATION_VERSION,
        "plan_domain_version": PLAN_DOMAIN_VERSION,
        "plan_identity_version": PLAN_IDENTITY_VERSION,
        "plan_lineage_version": PLAN_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_plan_lineage(plan_id: str, *, parents: Sequence[str] = (), category: str = "",
                      reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                      extra: dict | None = None) -> LineageRecord:
    """A plan lineage node parented by the approved goal (+ deps) it derives from."""
    outputs = {"plan_id": plan_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind="plan", versions=plan_version_bundle(),
        inputs={"plan_id": plan_id, "category": category, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


def make_relationship_lineage(dependency_id: str, *, parents: Sequence[str] = (),
                              relation: str = "", created_at: str = DETERMINISTIC_EPOCH
                              ) -> LineageRecord:
    """A plan-dependency lineage node parented by the related artifacts' nodes."""
    return make_lineage_record(
        kind="plan_dependency", versions=plan_version_bundle(),
        inputs={"dependency_id": dependency_id, "relation": relation},
        outputs={"dependency_id": dependency_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
