"""Deterministic state-evolution tracking (V3-P2).

An evolution record is the ordered sequence of *state transitions* a subject
underwent, derived from its lifecycle events. The destination state of each step
is inferred deterministically from the event type's taxonomy (e.g.
``CASE_CONFIRMED`` -> ``confirmed``); the ``from_state`` is the previous step's
``to_state``. No hidden state is reconstructed — only the recorded lifecycle events
are read.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..identity import mint_evolution
from ..models.domain import EvolutionRecord, EvolutionStep
from ..timelines import EventSourceView

# Event types that represent a lifecycle state change -> the state they land in.
# Derived from the V3-P1 taxonomy; only state-changing events appear here.
_STATE_OF: dict[str, str] = {
    # case
    "CASE_CREATED": "created", "CASE_INGESTED": "ingested", "CASE_PROCESSING": "processing",
    "CASE_READY_FOR_REVIEW": "ready_for_review", "CASE_UNDER_REVIEW": "under_review",
    "CASE_REVIEWED": "reviewed", "CASE_CLOSED": "closed", "CASE_ARCHIVED": "archived",
    # review
    "REVIEW_CREATED": "created", "REVIEW_ASSIGNED": "assigned", "REVIEW_STARTED": "in_progress",
    "REVIEW_SUBMITTED": "pending_confirmation", "REVIEW_COMPLETED": "completed",
    "REVIEW_REOPENED": "reopened", "REVIEW_CLOSED": "closed", "REVIEW_ARCHIVED": "archived",
    # finding
    "FINDING_CREATED": "created", "FINDING_DRAFTED": "draft", "FINDING_SUBMITTED": "under_review",
    "FINDING_CONFIRMED": "confirmed", "FINDING_REVISED": "revised",
    "FINDING_SUPERSEDED": "superseded", "FINDING_CLOSED": "closed", "FINDING_ARCHIVED": "archived",
}


class EvolutionEngine:
    """Builds :class:`EvolutionRecord` artifacts from lifecycle events (read-only)."""

    def build(self, view: EventSourceView, *, subject_kind: str, subject_id: str,
              source_entity_ids: Sequence[str]) -> EvolutionRecord:
        events = view.for_sources(source_entity_ids)
        steps: list[EvolutionStep] = []
        prev_state: Optional[str] = None
        order = 0
        for e in events:
            to_state = _STATE_OF.get(e.event_type)
            if to_state is None:
                continue  # not a state-changing event
            steps.append(EvolutionStep(order=order, from_state=prev_state, to_state=to_state,
                                       event_id=e.event_id, event_type=e.event_type))
            prev_state = to_state
            order += 1
        scope = f"{subject_kind}:{subject_id}"
        ident = mint_evolution(scope)
        return EvolutionRecord(evolution_id=ident.id, scope=scope, subject_kind=subject_kind,
                               subject_id=subject_id, steps=tuple(steps))

    def build_for_entity(self, view: EventSourceView, *, subject_kind: str,
                         subject_id: str) -> EvolutionRecord:
        return self.build(view, subject_kind=subject_kind, subject_id=subject_id,
                          source_entity_ids=[subject_id])
