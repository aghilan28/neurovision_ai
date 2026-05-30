"""Event generation framework — adapters that observe V2 systems (V3-P1)."""

from __future__ import annotations

from .adapters import (
    CaseEventAdapter, ReviewEventAdapter, FindingEventAdapter, KnowledgeEventAdapter,
    IntelligenceEventAdapter, DecisionEventAdapter, ADAPTERS,
)

__all__ = [
    "CaseEventAdapter", "ReviewEventAdapter", "FindingEventAdapter", "KnowledgeEventAdapter",
    "IntelligenceEventAdapter", "DecisionEventAdapter", "ADAPTERS",
]
