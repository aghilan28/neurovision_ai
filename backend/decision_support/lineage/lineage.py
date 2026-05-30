"""Decision-support lineage helpers built on ml.lineage.

Every decision-support artifact gets a content-addressed lineage node whose
*parents* are the lineage nodes it derives from: the context node parents the
case/review/finding/interpretation/concept nodes; evidence/risk/prioritization/
guidance nodes parent the context node; the decision-support record parents them
all. A single ``verify_chain`` from any decision node therefore spans back to the
patient roots — every recommendation is fully traceable.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    DECISION_SUPPORT_VERSION, DECISION_DOMAIN_VERSION, DECISION_IDENTITY_VERSION,
    DECISION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def decision_version_bundle(**extra: object) -> dict:
    bundle = {
        "decision_support_version": DECISION_SUPPORT_VERSION,
        "decision_domain_version": DECISION_DOMAIN_VERSION,
        "decision_identity_version": DECISION_IDENTITY_VERSION,
        "decision_lineage_version": DECISION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_decision_lineage(kind: str, artifact_id: str, *, parents: Sequence[str] = (),
                          case_id: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A generic decision-support lineage node parented by its source/context nodes."""
    return make_lineage_record(
        kind=kind, versions=decision_version_bundle(),
        inputs={"artifact_id": artifact_id, "case_id": case_id, "n_parents": len(tuple(parents))},
        outputs={"artifact_id": artifact_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
