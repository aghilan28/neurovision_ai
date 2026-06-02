"""Prioritization engine (V3-P6).

Generates explainable :class:`RecommendationPriority` assignments: a priority level
(low|medium|high|critical), the deterministic [0,1] score it derives from, a
human-readable reason, and the supporting metrics/risks/trends/workflow signals.
All prioritization must be explainable — every assignment carries the exact signals
that produced it.

The mapping from score to level is a fixed, deterministic banding so identical
inputs always reproduce the same priority.
"""

from __future__ import annotations

from typing import Sequence

from ..models.kinds import PriorityLevel
from ..models.domain import RecommendationPriority
from ..version import RECOMMENDATION_PRIORITIZATION_ENGINE_VERSION
from ..context import rnd

# Fixed score -> level banding (deterministic, explainable).
_BANDS = ((0.75, PriorityLevel.CRITICAL), (0.5, PriorityLevel.HIGH),
          (0.25, PriorityLevel.MEDIUM), (0.0, PriorityLevel.LOW))


def level_for_score(score: float) -> str:
    for threshold, level in _BANDS:
        if score >= threshold:
            return level
    return PriorityLevel.LOW


class PrioritizationEngine:
    """Builds explainable :class:`RecommendationPriority` assignments (deterministic)."""

    engine_version = RECOMMENDATION_PRIORITIZATION_ENGINE_VERSION

    def prioritize(self, *, score: float, reason: str,
                   supporting_metrics: Sequence[str] = (),
                   supporting_risks: Sequence[str] = (),
                   supporting_trends: Sequence[str] = (),
                   supporting_workflow: Sequence[str] = ()) -> RecommendationPriority:
        score = max(0.0, min(1.0, rnd(score)))
        level = level_for_score(score)
        return RecommendationPriority(
            level=level, score=score, reason=reason,
            supporting_metrics=tuple(supporting_metrics), supporting_risks=tuple(supporting_risks),
            supporting_trends=tuple(supporting_trends),
            supporting_workflow=tuple(supporting_workflow))

    def from_risk(self, view, risk_metric: str, *, reason: str,
                  supporting_workflow: Sequence[str] = ()) -> RecommendationPriority:
        """Priority derived directly from a risk score (higher risk = higher priority)."""
        from backend.operational_analytics import AnalyticsCategory as AC
        score = view.metric_value(AC.RISK, risk_metric, 0.0)
        return self.prioritize(score=score, reason=reason,
                               supporting_risks=[risk_metric],
                               supporting_workflow=supporting_workflow)
