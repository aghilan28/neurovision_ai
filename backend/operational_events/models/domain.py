"""Operational event domain entities (V3-P1).

Events are **facts**: immutable, versioned, traceable. They are never edited; they
may be **superseded** (a new event references the one it supersedes), never
rewritten. Each entity is pure data + ``to_dict`` + (where relevant) a content
``state_signature`` used for versioning.

The mandated entities: ``EventIdentity`` (in ``identity``), ``EventRecord``,
``EventMetadata``, ``EventType``/``EventCategory`` (in ``taxonomy``),
``EventVersion``, ``EventAuditRecord``, ``EventLineageRecord``,
``EventRegistryRecord``, ``EventRelationship``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    EVENT_DOMAIN_VERSION, EVENT_REGISTRY_VERSION, EVENT_RELATIONSHIP_VERSION,
    DETERMINISTIC_EPOCH,
)
from ..identity import LogicalClock


# --- event metadata -----------------------------------------------------------
@dataclass(frozen=True)
class EventMetadata:
    """Descriptive, non-identifying metadata attached to an event.

    ``source_kind`` is the observed subsystem (case/review/finding/...);
    ``source_audit_event_hash`` pins the exact immutable source audit entry the
    event was derived from (proving the event is observed, not invented).
    """

    source_kind: str
    source_audit_event_hash: str
    actor: str = "system"
    summary: str = ""
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"source_kind": self.source_kind,
                "source_audit_event_hash": self.source_audit_event_hash,
                "actor": self.actor, "summary": self.summary, "attributes": self.attributes}


# --- event record (the fact) --------------------------------------------------
@dataclass(frozen=True)
class EventRecord:
    """An immutable operational event — a recorded fact about a change."""

    event_id: str
    event_type: str
    category: str
    source_entity_id: str
    source_version: str
    clock: LogicalClock
    metadata: EventMetadata
    payload: dict = field(default_factory=dict)
    supersedes: Optional[str] = None          # event_id this supersedes (never rewrite)
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    status: str = "active"                     # active | superseded
    domain_version: str = EVENT_DOMAIN_VERSION

    def state_signature(self) -> str:
        """Content signature of the immutable *fact* (excludes assigned version/
        lineage/audit/status, which are governance bookkeeping)."""
        return hash_obj({
            "event_id": self.event_id, "event_type": self.event_type,
            "category": self.category, "source_entity_id": self.source_entity_id,
            "source_version": self.source_version, "clock": self.clock.to_dict(),
            "metadata": self.metadata.to_dict(), "payload": self.payload,
            "supersedes": self.supersedes,
        })

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id, "event_type": self.event_type, "category": self.category,
            "source_entity_id": self.source_entity_id, "source_version": self.source_version,
            "clock": self.clock.to_dict(), "metadata": self.metadata.to_dict(),
            "payload": self.payload, "supersedes": self.supersedes, "status": self.status,
            "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }


# --- event relationship -------------------------------------------------------
@dataclass(frozen=True)
class EventRelationship:
    """A directed edge from an event to another entity or event.

    ``relation`` describes the edge kind: ``observes`` (event→source entity),
    ``causal`` / ``sequence`` / ``depends_on`` (event→event), etc.
    """

    relationship_id: str
    source_event_id: str
    target_id: str
    target_kind: str          # case|review|finding|knowledge|intelligence|decision|event|patient
    relation: str             # observes|causal|sequence|depends_on|supersedes
    relationship_version: str = EVENT_RELATIONSHIP_VERSION

    def state_signature(self) -> str:
        return hash_obj({"relationship_id": self.relationship_id,
                         "source_event_id": self.source_event_id, "target_id": self.target_id,
                         "target_kind": self.target_kind, "relation": self.relation})

    def to_dict(self) -> dict:
        return {"relationship_id": self.relationship_id, "source_event_id": self.source_event_id,
                "target_id": self.target_id, "target_kind": self.target_kind,
                "relation": self.relation, "relationship_version": self.relationship_version}


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class EventAuditRecord:
    """An immutable audit event; field-compatible with ``CaseAuditRecord``."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class EventVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


@dataclass(frozen=True)
class EventLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class EventRegistryRecord:
    """The registry entry shape for an event."""

    event_id: str
    event_type: str
    category: str
    source_entity_id: str
    version: str
    lineage_id: str
    audit_state: str
    status: str
    content_signature_value: str
    event_registry_version: str = EVENT_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"event_id": self.event_id, "event_type": self.event_type,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "status": self.status, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"event_id": self.event_id, "event_type": self.event_type, "category": self.category,
                "source_entity_id": self.source_entity_id, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state, "status": self.status,
                "content_signature_value": self.content_signature_value,
                "event_registry_version": self.event_registry_version,
                "content_signature": self.content_signature()}
