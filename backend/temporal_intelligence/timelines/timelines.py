"""Deterministic timeline generation (V3-P2).

A timeline is the deterministically-ordered sequence of events for a subject
(patient / case / review / finding / knowledge / decision / operational). It is
derived strictly from the recorded events via the :class:`EventSourceView`; every
timeline is reproducible because the ordering is the events' logical clock.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_timeline
from ..models.domain import Timeline, TimelinePoint
from .event_source import EventSourceView


class TimelineEngine:
    """Builds :class:`Timeline` artifacts from an event-source view (read-only)."""

    def build(self, view: EventSourceView, *, subject_kind: str, subject_id: str,
              source_entity_ids: Sequence[str]) -> Timeline:
        """Build a timeline for a subject spanning the given source entity ids."""
        events = view.for_sources(source_entity_ids)
        points = tuple(
            TimelinePoint(order=i, event_id=e.event_id, event_type=e.event_type,
                          category=e.category, clock=e.clock.to_dict())
            for i, e in enumerate(events))
        scope = f"{subject_kind}:{subject_id}"
        ident = mint_timeline(scope)
        return Timeline(timeline_id=ident.id, scope=scope, subject_kind=subject_kind,
                        subject_id=subject_id, points=points)

    def build_for_entity(self, view: EventSourceView, *, subject_kind: str,
                         subject_id: str) -> Timeline:
        """Convenience: timeline for a single source entity (id == subject_id)."""
        return self.build(view, subject_kind=subject_kind, subject_id=subject_id,
                          source_entity_ids=[subject_id])

    def build_operational(self, view: EventSourceView) -> Timeline:
        """The whole-platform operational timeline (every event, in logical order)."""
        events = view.all()
        points = tuple(
            TimelinePoint(order=i, event_id=e.event_id, event_type=e.event_type,
                          category=e.category, clock=e.clock.to_dict())
            for i, e in enumerate(events))
        scope = "operational:all"
        ident = mint_timeline(scope)
        return Timeline(timeline_id=ident.id, scope=scope, subject_kind="operational",
                        subject_id="all", points=points)
