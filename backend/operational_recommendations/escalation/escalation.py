"""Escalation framework (V3-P6).

Generates escalation **candidates** — never automatic escalations. Each candidate
carries its reason, the evidence behind it, the risk context that motivated it, and
an explainable priority. The framework identifies *where* escalation review might
be warranted from operational risk; a human decides whether to act. Nothing here
escalates anything.
"""

from __future__ import annotations

from typing import Optional

from backend.operational_analytics import AnalyticsCategory as AC

from ..identity import mint_recommendation
from ..models.kinds import RecommendationKind, PriorityLevel
from ..models.domain import RecommendationRecord
from ..models.source import RecommendationSourceView
from ..prioritization import PrioritizationEngine
from ..version import RECOMMENDATION_ESCALATION_ENGINE_VERSION
from ..context import analytics_evidence, make_evidence

# Risk dimensions that can each motivate an escalation candidate.
_RISK_DIMENSIONS = (
    ("operational_risk", "operational risk profile elevated"),
    ("workflow_risk", "workflow incompletion/rework risk elevated"),
    ("quality_risk", "quality defect risk elevated"),
    ("bottleneck_risk", "bottleneck congestion risk elevated"),
    ("dependency_risk", "blocked/waiting dependency risk elevated"),
    ("knowledge_risk", "knowledge gap risk elevated"),
)

# A candidate is only emitted when the risk score is at/above this threshold.
ESCALATION_THRESHOLD = 0.5


class EscalationEngine:
    """Builds escalation-candidate records (read-only; no automatic escalation)."""

    engine_version = RECOMMENDATION_ESCALATION_ENGINE_VERSION

    def __init__(self) -> None:
        self._prio = PrioritizationEngine()

    def _record(self, *, risk_metric: str, score: float, reason: str, evidence,
                view: RecommendationSourceView, context_id: Optional[str]) -> RecommendationRecord:
        scope = f"{RecommendationKind.ESCALATION}:{risk_metric}:all"
        ident = mint_recommendation(RecommendationKind.ESCALATION, scope)
        prio = self._prio.prioritize(
            score=score, reason=reason, supporting_risks=[risk_metric],
            supporting_workflow=list(view.workflow_ids()))
        analytics_ids = tuple(sorted({e.source_id for e in evidence
                                      if e.source_kind == "analytics"}))
        statement = (f"Escalation candidate: {reason} (risk={score:.2f}). "
                     "Recommend human escalation review; no automatic escalation taken.")
        return RecommendationRecord(
            recommendation_id=ident.id, kind=RecommendationKind.ESCALATION, scope=scope,
            subject_kind="operational", subject_id="all", statement=statement, priority=prio,
            evidence=tuple(evidence), context_id=context_id, analytics_ids=analytics_ids,
            workflow_ids=tuple(view.workflow_ids()), graph_ids=tuple(view.graph_node_ids()),
            rationale=f"derived from analytics {risk_metric}; escalation requires human decision")

    def build(self, view: RecommendationSourceView, *,
              context_id: Optional[str] = None) -> list[RecommendationRecord]:
        out: list[RecommendationRecord] = []
        for risk_metric, reason in _RISK_DIMENSIONS:
            score = view.metric_value(AC.RISK, risk_metric, 0.0)
            if score < ESCALATION_THRESHOLD:
                continue  # not a candidate (deterministic threshold)
            evidence = [e for e in [analytics_evidence(view, AC.RISK, risk_metric),
                                    analytics_evidence(view, AC.HEALTH, "operational_health")] if e]
            # attach the risk-context evidence explicitly (escalation risk context)
            risk_rec = view.first_of_category(AC.RISK)
            if risk_rec is not None:
                evidence.append(make_evidence(
                    source_kind="analytics", source_id=risk_rec.analytics_id,
                    metric_name="risk_context", value=score,
                    detail=f"risk context for {risk_metric}", lineage_id=risk_rec.lineage_id))
            out.append(self._record(risk_metric=risk_metric, score=score, reason=reason,
                                    evidence=evidence, view=view, context_id=context_id))
        return out

    def is_critical(self, record: RecommendationRecord) -> bool:
        return record.priority.level == PriorityLevel.CRITICAL
