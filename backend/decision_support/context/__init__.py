"""Decision context system.

Aggregates case/review/finding/interpretation/knowledge/evidence (and optional
population) context into a deterministic :class:`DecisionContext` bundle.
"""

from backend.decision_support.context.aggregator import ContextAggregator

__all__ = ["ContextAggregator"]
