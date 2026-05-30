"""Deterministic event-source view for temporal intelligence (V3-P2).

Wraps an :class:`EventRegistry` and exposes events in a single, deterministic
**logical order** so every temporal artifact is reproducible. Ordering key is the
event's logical clock plus its id as a final tiebreaker:

    (ingestion_ordinal, source_seq, epoch, event_id)

This is the *only* way temporal intelligence reads events — no hidden state
reconstruction; everything is derived from the registered event facts.
"""

from __future__ import annotations

from typing import Sequence


def _order_key(rec) -> tuple:
    clock = rec_clock(rec)
    return (clock["ingestion_ordinal"], clock["source_seq"], clock["epoch"], rec.event_id)


def rec_clock(rec) -> dict:
    """Return an event registry record's logical clock as a dict.

    The registry record itself does not carry the clock, so the source view is
    constructed from the full EventRecord objects (which do). See EventSourceView.
    """
    return rec  # overridden below; placeholder for type clarity


class EventSourceView:
    """An immutable, deterministically-ordered view over recorded events.

    Constructed from the full :class:`EventRecord` objects (which carry the logical
    clock) so ordering is exact and reproducible.
    """

    def __init__(self, events: Sequence) -> None:
        # events: Sequence[EventRecord]
        self._events = sorted(events, key=self._key)

    @staticmethod
    def _key(ev) -> tuple:
        c = ev.clock.to_dict() if hasattr(ev.clock, "to_dict") else dict(ev.clock)
        return (c["ingestion_ordinal"], c["source_seq"], c["epoch"], ev.event_id)

    def all(self) -> list:
        return list(self._events)

    def active(self) -> list:
        return [e for e in self._events if getattr(e, "status", "active") == "active"]

    def for_source(self, source_entity_id: str) -> list:
        return [e for e in self._events if e.source_entity_id == source_entity_id]

    def for_sources(self, source_entity_ids: Sequence[str]) -> list:
        wanted = set(source_entity_ids)
        return [e for e in self._events if e.source_entity_id in wanted]

    def by_category(self, category: str) -> list:
        return [e for e in self._events if e.category == category]

    def source_ids(self) -> list:
        seen = []
        for e in self._events:
            if e.source_entity_id not in seen:
                seen.append(e.source_entity_id)
        return seen

    def __len__(self) -> int:
        return len(self._events)
