"""Policy-layer lineage helpers built on ml.lineage.

Every policy, constraint, and evaluation gets a content-addressed lineage node.

  * A **policy** node parents the goals/governance artifacts that motivated it (when
    supplied); a root governance policy may have no upstream parent.
  * A **constraint** node parents its owning policy node.
  * An **evaluation** node parents both the policy node and the subject's lineage
    node (e.g. the goal being evaluated) — so an evaluation traces to the goal and,
    through it, back through operational intelligence to the patient.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    POLICY_ENGINE_VERSION, POLICY_DOMAIN_VERSION, POLICY_IDENTITY_VERSION,
    POLICY_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def policy_version_bundle(**extra: object) -> dict:
    bundle = {
        "policy_engine_version": POLICY_ENGINE_VERSION,
        "policy_domain_version": POLICY_DOMAIN_VERSION,
        "policy_identity_version": POLICY_IDENTITY_VERSION,
        "policy_lineage_version": POLICY_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def _node(kind: str, the_id: str, *, parents: Sequence[str], reason: str, created_at: str,
          extra: dict | None = None) -> LineageRecord:
    outputs = {"id": the_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind=kind, versions=policy_version_bundle(),
        inputs={"id": the_id, "n_parents": len(tuple(parents))}, outputs=outputs,
        parents=tuple(p for p in parents if p), created_at=created_at)


def make_policy_lineage(policy_id: str, *, parents: Sequence[str] = (), reason: str = "created",
                        created_at: str = DETERMINISTIC_EPOCH, extra: dict | None = None
                        ) -> LineageRecord:
    return _node("policy", policy_id, parents=parents, reason=reason, created_at=created_at,
                 extra=extra)


def make_constraint_lineage(constraint_id: str, *, parents: Sequence[str] = (),
                            created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return _node("policy_constraint", constraint_id, parents=parents, reason="created",
                 created_at=created_at)


def make_evaluation_lineage(evaluation_id: str, *, parents: Sequence[str] = (),
                            outcome: str = "", created_at: str = DETERMINISTIC_EPOCH
                            ) -> LineageRecord:
    return _node("policy_evaluation", evaluation_id, parents=parents, reason="evaluated",
                 created_at=created_at, extra={"outcome": outcome})
