"""Optimization engine (V3-P6).

Generates explainable optimization **suggestions**: workflow optimization,
dependency optimization, queue optimization, and process optimization. Every
suggestion cites evidence and links to the analytics/workflows it derives from.

**No autonomous execution** — these are suggestions only. The engine never mutates
a workflow, never reorders a queue, never changes a dependency; it only describes a
candidate improvement and the evidence behind it.
"""

from __future__ import annotations

from typing import Optional

from backend.operational_analytics import AnalyticsCategory as AC

from ..identity import mint_recommendation
from ..models.kinds import RecommendationKind
from ..models.domain import RecommendationRecord
from ..models.source import RecommendationSourceView
from ..prioritization import PrioritizationEngine
from ..version import RECOMMENDATION_OPTIMIZATION_ENGINE_VERSION
from ..context import analytics_evidence


class OptimizationEngine:
    """Builds optimization-suggestion records (read-only, deterministic, no execution)."""

    engine_version = RECOMMENDATION_OPTIMIZATION_ENGINE_VERSION

    def __init__(self) -> None:
        self._prio = PrioritizationEngine()

    def _record(self, *, area: str, subject_kind: str, subject_id: str, statement: str,
                priority, evidence, view: RecommendationSourceView,
                context_id: Optional[str], rationale: str) -> RecommendationRecord:
        scope = f"{RecommendationKind.OPTIMIZATION}:{area}:{subject_id}"
        ident = mint_recommendation(RecommendationKind.OPTIMIZATION, scope)
        analytics_ids = tuple(sorted({e.source_id for e in evidence
                                      if e.source_kind == "analytics"}))
        return RecommendationRecord(
            recommendation_id=ident.id, kind=RecommendationKind.OPTIMIZATION, scope=scope,
            subject_kind=subject_kind, subject_id=subject_id, statement=statement,
            priority=priority, evidence=tuple(evidence), context_id=context_id,
            analytics_ids=analytics_ids, workflow_ids=tuple(view.workflow_ids()),
            graph_ids=tuple(view.graph_node_ids()), rationale=rationale)

    def build(self, view: RecommendationSourceView, *,
              context_id: Optional[str] = None) -> list[RecommendationRecord]:
        out: list[RecommendationRecord] = []

        # --- workflow optimization (driven by workflow risk / rework) --------
        workflow_risk = view.metric_value(AC.RISK, "workflow_risk", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.RISK, "workflow_risk"),
                          analytics_evidence(view, AC.PERFORMANCE, "transition_performance")] if e]
        if ev:
            prio = self._prio.prioritize(score=workflow_risk,
                                         reason="workflow incompletion/rework risk",
                                         supporting_risks=["workflow_risk"],
                                         supporting_metrics=["transition_performance"])
            stmt = ("Suggestion: reduce workflow rework and incomplete transitions to raise "
                    "completion" if workflow_risk > 0 else
                    "Suggestion: workflows are efficient; no workflow optimization indicated")
            out.append(self._record(area="workflow", subject_kind="workflow", subject_id="all",
                                    statement=stmt, priority=prio, evidence=ev, view=view,
                                    context_id=context_id,
                                    rationale="derived from analytics workflow risk + transition performance"))

        # --- dependency optimization (driven by dependency risk) -------------
        dependency_risk = view.metric_value(AC.RISK, "dependency_risk", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.RISK, "dependency_risk")] if e]
        if ev:
            prio = self._prio.prioritize(score=dependency_risk,
                                         reason="waiting/blocked dependency share",
                                         supporting_risks=["dependency_risk"])
            stmt = ("Suggestion: unblock waiting/blocked dependencies to improve flow"
                    if dependency_risk > 0 else
                    "Suggestion: dependencies are not blocking; no dependency optimization indicated")
            out.append(self._record(area="dependency", subject_kind="workflow", subject_id="all",
                                    statement=stmt, priority=prio, evidence=ev, view=view,
                                    context_id=context_id,
                                    rationale="derived from analytics dependency risk"))

        # --- queue optimization (driven by review performance) ---------------
        review_perf = view.metric_value(AC.PERFORMANCE, "review_performance", 1.0)
        ev = [e for e in [analytics_evidence(view, AC.PERFORMANCE, "review_performance"),
                          analytics_evidence(view, AC.QUALITY, "review_quality")] if e]
        if ev:
            prio = self._prio.prioritize(score=1.0 - review_perf,
                                         reason="review-queue completion shortfall",
                                         supporting_metrics=["review_performance", "review_quality"])
            stmt = ("Suggestion: rebalance the review queue to lift completion of started reviews"
                    if review_perf < 1.0 else
                    "Suggestion: review queue throughput is healthy; no queue optimization indicated")
            out.append(self._record(area="queue", subject_kind="queue", subject_id="reviews",
                                    statement=stmt, priority=prio, evidence=ev, view=view,
                                    context_id=context_id,
                                    rationale="derived from analytics review performance + quality"))

        # --- process optimization (driven by overall quality) ----------------
        workflow_quality = view.metric_value(AC.QUALITY, "workflow_quality", 1.0)
        ev = [e for e in [analytics_evidence(view, AC.QUALITY, "workflow_quality"),
                          analytics_evidence(view, AC.TREND, "operational_trend")] if e]
        if ev:
            prio = self._prio.prioritize(score=1.0 - workflow_quality,
                                         reason="operational process quality",
                                         supporting_metrics=["workflow_quality"],
                                         supporting_trends=["operational_trend"])
            stmt = ("Suggestion: tighten the operational process where quality dips"
                    if workflow_quality < 1.0 else
                    "Suggestion: process quality is high; no process optimization indicated")
            out.append(self._record(area="process", subject_kind="operational", subject_id="all",
                                    statement=stmt, priority=prio, evidence=ev, view=view,
                                    context_id=context_id,
                                    rationale="derived from analytics workflow quality + operational trend"))

        return out
