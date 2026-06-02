"""Persistence lineage helpers built on the shared ``ml.lineage`` machinery (DRP4-L).

No parallel lineage system: the persistence-record and recovery-event nodes are recorded in
the *same* ``ml.lineage.LineageTracker`` as every upstream node. A persistence record parents
the **anchor** node (a representative served execution/response — which already chains
model → inference → dataset → patient); a recovery event parents the persistence node — so a
single ``verify_chain`` from a recovery event reaches the patient:

    Dataset -> Model -> Inference -> Serving -> Persistence Record -> Recovery Event
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    PERSISTENCE_PLATFORM_VERSION, PERSISTENCE_DOMAIN_VERSION, PERSISTENCE_IDENTITY_VERSION,
    PERSISTENCE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)

__all__ = ["make_persistence_lineage", "make_recovery_lineage", "persistence_version_bundle"]


def persistence_version_bundle(**extra: object) -> dict:
    bundle = {
        "persistence_platform_version": PERSISTENCE_PLATFORM_VERSION,
        "persistence_domain_version": PERSISTENCE_DOMAIN_VERSION,
        "persistence_identity_version": PERSISTENCE_IDENTITY_VERSION,
        "persistence_lineage_version": PERSISTENCE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_persistence_lineage(persistence_id: str, anchor_lineage_id: str | None, *,
                             snapshot_fingerprint: str,
                             created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A persistence-record node parented on the anchor served-artifact node (if any)."""
    parents = (anchor_lineage_id,) if anchor_lineage_id else ()
    return make_lineage_record(
        kind="persistence_record", versions=persistence_version_bundle(),
        inputs={"anchor_lineage_id": anchor_lineage_id},
        outputs={"persistence_id": persistence_id, "snapshot_fingerprint": snapshot_fingerprint},
        parents=parents, created_at=created_at)


def make_recovery_lineage(recovery_id: str, persistence_lineage_id: str, *, status: str,
                          created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A recovery-event node parented on the persistence-record node."""
    return make_lineage_record(
        kind="recovery_event", versions=persistence_version_bundle(),
        inputs={"persistence_id": persistence_lineage_id},
        outputs={"recovery_id": recovery_id, "status": status}, parents=(persistence_lineage_id,),
        created_at=created_at)
