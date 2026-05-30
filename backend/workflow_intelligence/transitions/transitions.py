"""Transition engine (V3-P3).

Derives workflow transitions deterministically from events (and, equivalently, the
timelines/histories built over the same events). The destination state of each
lifecycle event is inferred from the V3-P2 ``_STATE_OF`` map (reused, not
duplicated), so transition semantics stay consistent with temporal evolution.
"""

from __future__ import annotations

from typing import Optional, Sequence

from backend.temporal_intelligence.evolution.evolution import _STATE_OF

from ..models.domain import WorkflowTransition


def derive_transitions(events: Sequence) -> list[WorkflowTransition]:
    """Ordered transitions for a subject's events (only state-changing events)."""
    transitions: list[WorkflowTransition] = []
    prev_state: Optional[str] = None
    order = 0
    for e in events:
        to_state = _STATE_OF.get(e.event_type)
        if to_state is None:
            continue
        transitions.append(WorkflowTransition(order=order, from_state=prev_state,
                                              to_state=to_state, event_id=e.event_id,
                                              event_type=e.event_type))
        prev_state = to_state
        order += 1
    return transitions


def transition_frequencies(transitions: Sequence[WorkflowTransition]) -> dict:
    """Count of each ``from->to`` transition (deterministic, sorted)."""
    freq: dict = {}
    for t in transitions:
        key = f"{t.from_state or 'START'}->{t.to_state}"
        freq[key] = freq.get(key, 0) + 1
    return dict(sorted(freq.items()))
