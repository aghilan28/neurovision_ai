"""Risk context system.

Aggregates inference/coverage/calibration/finding/evidence/knowledge/review risk
into an explainable :class:`RiskContext`. This is decision-support *review-
attention* risk (how much a human should look closely), never a clinical risk
score, diagnosis, or prognosis.
"""

from backend.decision_support.risk.aggregator import RiskContextAggregator

__all__ = ["RiskContextAggregator"]
