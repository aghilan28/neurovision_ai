"""Temporal-intelligence lineage helpers built on ml.lineage.

Every temporal artifact gets a content-addressed lineage node whose *parents* are
the lineage nodes of the **events** it was derived from. Because each event node
already traces back to its source entity and the patient, a single ``verify_chain``
from a temporal artifact spans Patient → ... → Event → Timeline/History/Evolution/
Analytics — complete traceability. The subsystem shares the platform's single
``ml.lineage.LineageTracker``.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    TEMPORAL_INTELLIGENCE_VERSION, TEMPORAL_DOMAIN_VERSION, TEMPORAL_IDENTITY_VERSION,
    TEMPORAL_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def temporal_version_bundle(**extra: object) -> dict:
    bundle = {
        "temporal_intelligence_version": TEMPORAL_INTELLIGENCE_VERSION,
        "temporal_domain_version": TEMPORAL_DOMAIN_VERSION,
        "temporal_identity_version": TEMPORAL_IDENTITY_VERSION,
        "temporal_lineage_version": TEMPORAL_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_temporal_lineage(kind: str, artifact_id: str, *, parents: Sequence[str] = (),
                          scope: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A temporal lineage node parented by the event nodes it derives from."""
    return make_lineage_record(
        kind=kind, versions=temporal_version_bundle(),
        inputs={"artifact_id": artifact_id, "scope": scope, "n_parents": len(tuple(parents))},
        outputs={"artifact_id": artifact_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
