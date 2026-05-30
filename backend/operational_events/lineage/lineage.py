"""Operational-event lineage helpers built on ml.lineage.

Every event gets a content-addressed lineage node whose *parent* is the lineage
node of the source entity it observes (the case/review/finding/... node in the
shared tracker). A single ``verify_chain`` from an event node therefore spans back
to the patient root — every event is fully traceable (Patient → ... → Event).

The event subsystem **shares** the platform's single ``ml.lineage.LineageTracker``
(passed in by the composition point); it never creates a parallel lineage system.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    OPERATIONAL_EVENTS_VERSION, EVENT_DOMAIN_VERSION, EVENT_IDENTITY_VERSION,
    EVENT_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def event_version_bundle(**extra: object) -> dict:
    bundle = {
        "operational_events_version": OPERATIONAL_EVENTS_VERSION,
        "event_domain_version": EVENT_DOMAIN_VERSION,
        "event_identity_version": EVENT_IDENTITY_VERSION,
        "event_lineage_version": EVENT_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_event_lineage(event_id: str, *, parents: Sequence[str] = (),
                       source_kind: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A content-addressed event lineage node parented by its source-entity node."""
    return make_lineage_record(
        kind="event", versions=event_version_bundle(),
        inputs={"event_id": event_id, "source_kind": source_kind, "n_parents": len(tuple(parents))},
        outputs={"event_id": event_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
