"""Deterministic history reconstruction (V3-P2).

A history is the ordered change-log of a subject, reconstructed **from events**
(never from hidden state). Each entry records the event, its type, a summary, and
the source version observed at that step — so the version history is recoverable
and deterministic.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_history
from ..models.domain import History, HistoryEntry
from ..timelines import EventSourceView


class HistoryEngine:
    """Builds :class:`History` artifacts from an event-source view (read-only)."""

    def build(self, view: EventSourceView, *, subject_kind: str, subject_id: str,
              source_entity_ids: Sequence[str]) -> History:
        events = view.for_sources(source_entity_ids)
        entries = tuple(
            HistoryEntry(order=i, event_id=e.event_id, event_type=e.event_type,
                         summary=e.metadata.summary or e.event_type,
                         source_version=e.source_version)
            for i, e in enumerate(events))
        scope = f"{subject_kind}:{subject_id}"
        ident = mint_history(scope)
        return History(history_id=ident.id, scope=scope, subject_kind=subject_kind,
                       subject_id=subject_id, entries=entries)

    def build_for_entity(self, view: EventSourceView, *, subject_kind: str,
                         subject_id: str) -> History:
        return self.build(view, subject_kind=subject_kind, subject_id=subject_id,
                          source_entity_ids=[subject_id])
