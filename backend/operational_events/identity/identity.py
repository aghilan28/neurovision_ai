"""Deterministic event identity generation (V3-P1).

An event identity is ``"event+{hash16}"`` — a sha256-derived digest of a canonical
payload: the source entity + source version + event type/category + the
**logical clock** coordinate. Properties: stable, deterministic, collision
resistant, traceable, versioned.

The logical clock is *not* a wall-clock timestamp (NR-9/NR-10 forbid wall-clock in
hashed content). It is the deterministic ordering coordinate carried by the
source audit event: ``(ingestion_ordinal, source_seq)`` plus the source's recorded
``created_at`` epoch string. Identical source facts therefore always mint the same
event id; a different occurrence (different source seq) mints a different id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EVENT_IDENTITY_VERSION

_ID_RE = re.compile(r"^event\+[0-9a-f]{16}$")
_REL_ID_RE = re.compile(r"^eventrel\+[0-9a-f]{16}$")


class EventIdentityError(ValueError):
    """Raised when event identity minting or validation fails."""


@dataclass(frozen=True)
class LogicalClock:
    """A deterministic ordering coordinate (never a wall-clock).

    * ``ingestion_ordinal`` — the order in which a source entity was observed by
      the generation framework (0-based, assigned deterministically by the run).
    * ``source_seq`` — the ``seq`` of the source audit event within its log.
    * ``epoch`` — the source's recorded ``created_at`` (the deterministic epoch).
    """

    ingestion_ordinal: int
    source_seq: int
    epoch: str

    def key(self) -> tuple[int, int, str]:
        return (self.ingestion_ordinal, self.source_seq, self.epoch)

    def to_dict(self) -> dict:
        return {"ingestion_ordinal": self.ingestion_ordinal,
                "source_seq": self.source_seq, "epoch": self.epoch}


@dataclass(frozen=True)
class EventIdentity:
    id: str
    event_type: str
    category: str
    source_entity_id: str
    source_version: str
    clock: LogicalClock
    identity_version: str = EVENT_IDENTITY_VERSION

    def to_dict(self) -> dict:
        return {"id": self.id, "event_type": self.event_type, "category": self.category,
                "source_entity_id": self.source_entity_id, "source_version": self.source_version,
                "clock": self.clock.to_dict(), "identity_version": self.identity_version}


def mint_event(*, event_type: str, category: str, source_entity_id: str,
               source_version: str, clock: LogicalClock) -> EventIdentity:
    """Mint a deterministic, content-addressed event identity."""
    if not event_type or not category:
        raise EventIdentityError("event_type and category must be non-empty")
    if not source_entity_id:
        raise EventIdentityError("source_entity_id must be non-empty")
    payload = {
        "identity_version": EVENT_IDENTITY_VERSION,
        "event_type": event_type,
        "category": category,
        "source_entity_id": source_entity_id,
        "source_version": source_version,
        "clock": clock.to_dict(),
    }
    return EventIdentity(id=f"event+{hash_obj(payload)}", event_type=event_type,
                         category=category, source_entity_id=source_entity_id,
                         source_version=source_version, clock=clock)


def mint_relationship(*, source_event_id: str, target_id: str, relation: str) -> str:
    """Mint a deterministic id for an event relationship edge."""
    if not source_event_id or not target_id or not relation:
        raise EventIdentityError("relationship endpoints and relation must be non-empty")
    payload = {"identity_version": EVENT_IDENTITY_VERSION, "source_event_id": source_event_id,
               "target_id": target_id, "relation": relation}
    return f"eventrel+{hash_obj(payload)}"


def validate_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed event identity {id_str!r}"
    return True, "ok"


def validate_relationship_identity(id_str: str) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _REL_ID_RE.match(id_str):
        return False, f"malformed event relationship identity {id_str!r}"
    return True, "ok"
