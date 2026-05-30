"""Guidance engine (V3-P6).

Generates explainable operational **guidance**: workflow guidance, review-queue
guidance, escalation guidance, operational guidance, and resource-awareness
guidance. Every guidance item cites **evidence** (a real analytics metric / risk /
workflow signal) and links to the analytics it derives from — no black-box
guidance. Guidance is a *suggestion*; nothing is executed.
"""

from __future__ import annotations

from typing import Optional

from backend.operational_analytics import AnalyticsCategory as AC

from ..identity import mint_recommendation
from ..models.kinds import RecommendationKind
from ..models.domain import RecommendationRecord
from ..models.source import RecommendationSourceView
from ..prioritization import PrioritizationEngine
from ..version import RECOMMENDATION_GUIDANCE_ENGINE_VERSION
from ..context import analytics_evidence


class GuidanceEngine:
    """Builds guidance :class:`RecommendationRecord` artifacts (read-only, deterministic)."""

    engine_version = RECOMMENDATION_GUIDANCE_ENGINE_VERSION

    def __init__(self) -> None:
        self._prio = PrioritizationEngine()

    def _record(self, *, scope_kind: str, subject_kind: str, subject_id: str, statement: str,
                priority, evidence, view: RecommendationSourceView, context_id: Optional[str],
                rationale: str) -> RecommendationRecord:
        scope = f"{RecommendationKind.GUIDANCE}:{scope_kind}:{subject_id}"
        ident = mint_recommendation(RecommendationKind.GUIDANCE, scope)
        analytics_ids = tuple(sorted({e.source_id for e in evidence
                                      if e.source_kind == "analytics"}))
        return RecommendationRecord(
            recommendation_id=ident.id, kind=RecommendationKind.GUIDANCE, scope=scope,
            subject_kind=subject_kind, subject_id=subject_id, statement=statement,
            priority=priority, evidence=tuple(evidence), context_id=context_id,
            analytics_ids=analytics_ids, workflow_ids=tuple(view.workflow_ids()),
            graph_ids=tuple(view.graph_node_ids()), rationale=rationale)

    def build(self, view: RecommendationSourceView, *,
              context_id: Optional[str] = None) -> list[RecommendationRecord]:
        out: list[RecommendationRecord] = []

        # --- workflow guidance (driven by bottleneck risk) -------------------
        bottleneck_risk = view.metric_value(AC.RISK, "bottleneck_risk", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.RISK, "bottleneck_risk"),
                          analytics_evidence(view, AC.QUALITY, "workflow_quality")] if e]
        if ev:
            prio = self._prio.prioritize(
                score=bottleneck_risk, reason="workflow bottleneck risk observed",
                supporting_risks=["bottleneck_risk"], supporting_metrics=["workflow_quality"])
            stmt = ("Review workflows showing bottlenecks; rework/stall conditions reduce "
                    "throughput") if bottleneck_risk > 0 else \
                   "Workflows show no bottleneck conditions; maintain current flow"
            out.append(self._record(scope_kind="workflow", subject_kind="workflow",
                                    subject_id="all", statement=stmt, priority=prio, evidence=ev,
                                    view=view, context_id=context_id,
                                    rationale="derived from analytics bottleneck risk + workflow quality"))

        # --- review-queue guidance (driven by review performance) ------------
        review_perf = view.metric_value(AC.PERFORMANCE, "review_performance", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.PERFORMANCE, "review_performance"),
                          analytics_evidence(view, AC.HEALTH, "review_health")] if e]
        if ev:
            # lower performance => higher attention score
            prio = self._prio.prioritize(
                score=1.0 - review_perf, reason="review-queue completion below ideal",
                supporting_metrics=["review_performance", "review_health"])
            stmt = ("Attend to the review queue; completion rate of started reviews is low"
                    if review_perf < 1.0 else
                    "Review queue is healthy; started reviews are completing")
            out.append(self._record(scope_kind="queue", subject_kind="queue", subject_id="reviews",
                                    statement=stmt, priority=prio, evidence=ev, view=view,
                                    context_id=context_id,
                                    rationale="derived from analytics review performance + health"))

        # --- escalation guidance (driven by operational risk) ----------------
        op_risk = view.metric_value(AC.RISK, "operational_risk", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.RISK, "operational_risk"),
                          analytics_evidence(view, AC.HEALTH, "operational_health")] if e]
        if ev:
            prio = self._prio.prioritize(score=op_risk, reason="operational risk profile",
                                         supporting_risks=["operational_risk"],
                                         supporting_metrics=["operational_health"])
            stmt = ("Consider escalation review where operational risk concentrates"
                    if op_risk >= 0.5 else
                    "Operational risk is within normal bounds; no escalation guidance")
            out.append(self._record(scope_kind="escalation", subject_kind="operational",
                                    subject_id="all", statement=stmt, priority=prio, evidence=ev,
                                    view=view, context_id=context_id,
                                    rationale="derived from analytics operational risk + health"))

        # --- operational guidance (driven by system health) ------------------
        system_health = view.metric_value(AC.HEALTH, "system_health_score", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.HEALTH, "system_health_score"),
                          analytics_evidence(view, AC.TREND, "operational_trend")] if e]
        if ev:
            prio = self._prio.prioritize(score=1.0 - system_health,
                                         reason="overall operational health signal",
                                         supporting_metrics=["system_health_score"],
                                         supporting_trends=["operational_trend"])
            stmt = (f"Operational health is {system_health:.2f}; "
                    + ("monitor closely" if system_health < 0.6 else "operating nominally"))
            out.append(self._record(scope_kind="operational", subject_kind="operational",
                                    subject_id="all", statement=stmt, priority=prio, evidence=ev,
                                    view=view, context_id=context_id,
                                    rationale="derived from analytics system health + operational trend"))

        # --- resource-awareness guidance (driven by throughput/velocity) -----
        efficiency = view.metric_value(AC.PERFORMANCE, "operational_efficiency", 0.0)
        ev = [e for e in [analytics_evidence(view, AC.PERFORMANCE, "operational_efficiency"),
                          analytics_evidence(view, AC.METRICS, "workflow_total")] if e]
        if ev:
            prio = self._prio.prioritize(score=1.0 - min(1.0, efficiency),
                                         reason="operational efficiency / resource awareness",
                                         supporting_metrics=["operational_efficiency",
                                                             "workflow_total"])
            stmt = ("Operational efficiency is low relative to recorded work; "
                    "be aware of resource load" if efficiency < 0.5 else
                    "Operational efficiency is adequate for the recorded work")
            out.append(self._record(scope_kind="resource", subject_kind="operational",
                                    subject_id="all", statement=stmt, priority=prio, evidence=ev,
                                    view=view, context_id=context_id,
                                    rationale="derived from analytics efficiency + workflow volume"))

        return out
