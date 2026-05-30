"""The event registry: governed, immutable, traceable operational events (V3-P1).

No event may exist outside the registry. Events are facts and are **never edited**:
re-registering the same ``event_id`` with different content is a forbidden silent
overwrite. An event may be **superseded** — recorded by flipping the superseded
event's status to ``superseded`` (a governed, audited state change that does not
rewrite the fact) and registering the new event that supersedes it.

The registry also stores event **relationships** (observes / causal / sequence /
depends_on / supersedes), keyed by relationship id.
"""

from __future__ import annotations

from dataclasses import replace

from ..version import EVENT_REGISTRY_VERSION
from ..models.domain import EventRegistryRecord, EventRelationship


class EventRegistry:
    """In-memory registry keyed by ``event_id`` (one record per event)."""

    def __init__(self) -> None:
        self._records: dict[str, EventRegistryRecord] = {}
        self._content_sigs: dict[str, str] = {}
        self._relationships: dict[str, EventRelationship] = {}

    # --- events ---------------------------------------------------------------
    def register(self, record: EventRegistryRecord) -> EventRegistryRecord:
        existing = self._records.get(record.event_id)
        sig = record.content_signature()
        if existing is not None:
            # Re-registering is only permitted when the *fact* is identical; the
            # only field allowed to differ is the governed status (active ->
            # superseded), which itself bumps the content signature deliberately.
            if (existing.content_signature_value != record.content_signature_value):
                raise ValueError(
                    f"event {record.event_id} already registered with different content "
                    "(events are immutable facts; silent overwrite forbidden)")
        self._records[record.event_id] = record
        self._content_sigs[record.event_id] = sig
        return record

    def mark_superseded(self, event_id: str) -> EventRegistryRecord:
        """Flip an event's status to ``superseded`` (governed; fact unchanged)."""
        rec = self.get(event_id)
        updated = replace(rec, status="superseded")
        self._records[event_id] = updated
        self._content_sigs[event_id] = updated.content_signature()
        return updated

    def get(self, event_id: str) -> EventRegistryRecord:
        if event_id not in self._records:
            raise KeyError(f"event {event_id!r} not in registry")
        return self._records[event_id]

    def exists(self, event_id: str) -> bool:
        return event_id in self._records

    def list_events(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.category == category)

    def by_type(self, event_type: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.event_type == event_type)

    def by_source(self, source_entity_id: str) -> list[str]:
        return sorted(eid for eid, r in self._records.items()
                      if r.source_entity_id == source_entity_id)

    def active(self) -> list[str]:
        return sorted(eid for eid, r in self._records.items() if r.status == "active")

    # --- relationships --------------------------------------------------------
    def register_relationship(self, rel: EventRelationship) -> EventRelationship:
        existing = self._relationships.get(rel.relationship_id)
        if existing is not None and existing.state_signature() != rel.state_signature():
            raise ValueError(
                f"relationship {rel.relationship_id} already registered with different content")
        self._relationships[rel.relationship_id] = rel
        return rel

    def relationship(self, relationship_id: str) -> EventRelationship:
        if relationship_id not in self._relationships:
            raise KeyError(f"relationship {relationship_id!r} not in registry")
        return self._relationships[relationship_id]

    def list_relationships(self) -> list[str]:
        return sorted(self._relationships)

    def relationships_for(self, source_event_id: str) -> list[EventRelationship]:
        return [self._relationships[rid] for rid in self.list_relationships()
                if self._relationships[rid].source_event_id == source_event_id]

    # --- serialization --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "event_registry_version": EVENT_REGISTRY_VERSION,
            "n_events": len(self._records),
            "n_active": len(self.active()),
            "n_relationships": len(self._relationships),
            "events": {eid: r.to_dict() for eid, r in sorted(self._records.items())},
            "relationships": {rid: r.to_dict() for rid, r in sorted(self._relationships.items())},
        }
