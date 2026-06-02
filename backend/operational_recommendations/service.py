"""OperationalRecommendationService — the governed orchestration hub for V3-P6.

Derives **explainable operational recommendations** (guidance, prioritization,
optimization suggestions, escalation candidates) from operational intelligence —
the V3-P5 analytics records (plus V3-P3 workflows and the V3-P4 graph for linking).
Each recommendation is admitted through one governed path: governance gate
(architecture/quality/context/risk) -> shared-lineage node parented by the analytics
lineage nodes it cites -> immutable audit event -> content-addressed version ->
registry sync.

Because each recommendation's lineage parents are analytics nodes (which trace
through workflow/graph/event/temporal nodes to the patient), a single
``verify_chain`` spans Patient -> ... -> Analytics -> Recommendation.
Recommendations are **suggestions only** — never executed, never auto-escalated.
This layer operates exclusively on operational intelligence — never clinical data.
Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .context import ContextEngine
from .guidance import GuidanceEngine
from .prioritization import PrioritizationEngine
from .optimization import OptimizationEngine
from .escalation import EscalationEngine
from .models.domain import RecommendationVersion, RecommendationRegistryRecord
from .models.source import RecommendationSourceView
from .audit import make_recommendation_audit_log
from .lineage import make_recommendation_lineage
from .registry import RecommendationRegistry
from .validation import RecommendationGovernanceGate, RecommendationValidator
from .reports import (
    build_guidance_report, build_priority_report, build_optimization_report,
    build_escalation_report, build_recommendation_report, build_validation_report,
    build_audit_report,
)



class OperationalRecommendationService:
    """Stateful service: recommendation registry, shared lineage tracker, audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[RecommendationRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or RecommendationRegistry()
        self.audit = make_recommendation_audit_log()
        self.gate = RecommendationGovernanceGate()
        self.validator = RecommendationValidator()
        self._context = ContextEngine()
        self._guidance = GuidanceEngine()
        self._prioritization = PrioritizationEngine()
        self._optimization = OptimizationEngine()
        self._escalation = EscalationEngine()
        self._view: Optional[RecommendationSourceView] = None

    # --- source view ----------------------------------------------------------
    def load_intelligence(self, *, analytics: Sequence = (), workflows: Sequence = (),
                          graph_registry=None) -> "OperationalRecommendationService":
        """Provide the operational intelligence to derive recommendations from."""
        self._view = RecommendationSourceView(analytics=analytics, workflows=workflows,
                                              graph_registry=graph_registry)
        return self

    def view(self) -> RecommendationSourceView:
        if self._view is None:
            raise RuntimeError("call load_intelligence(...) before deriving recommendations")
        return self._view

    # --- context --------------------------------------------------------------
    def build_context(self, *, scope: str = "operational:all",
                      created_at: str = DETERMINISTIC_EPOCH):
        """Build + register the deterministic context bundle (no governance gate)."""
        context = self._context.build(self.view(), scope=scope)
        self.registry.register_context(context)
        self.audit.append("context_built", {"context_id": context.context_id, "scope": scope},
                          created_at=created_at)
        return context

    # --- recommendation generation -------------------------------------------
    def generate(self, *, context_id: Optional[str] = None,
                 created_at: str = DETERMINISTIC_EPOCH) -> dict:
        """Generate + admit guidance, optimization and escalation recommendations.

        Returns a dict keyed by kind -> list[RecommendationRecord]. If no context
        is supplied, one is built and registered first (so every recommendation
        links to a registered context).
        """
        view = self.view()
        if context_id is None:
            context_id = self.build_context(created_at=created_at).context_id

        produced: dict = {"guidance": [], "optimization": [], "escalation": []}
        for rec in self._guidance.build(view, context_id=context_id):
            produced["guidance"].append(self._finalize(rec, view, created_at=created_at))
        for rec in self._optimization.build(view, context_id=context_id):
            produced["optimization"].append(self._finalize(rec, view, created_at=created_at))
        for rec in self._escalation.build(view, context_id=context_id):
            produced["escalation"].append(self._finalize(rec, view, created_at=created_at))
        return produced

    def all_records(self, produced: dict) -> list:
        out: list = []
        for recs in produced.values():
            out.extend(recs)
        return out

    # --- validation + reports -------------------------------------------------
    def validate(self, record):
        return self.validator.validate(record=record, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, records: Sequence) -> dict:
        records = list(records)
        return {
            "recommendation_report": build_recommendation_report(records),
            "guidance_report": build_guidance_report(records),
            "priority_report": build_priority_report(records),
            "optimization_report": build_optimization_report(records),
            "escalation_report": build_escalation_report(records),
            "audit_report": build_audit_report(self.audit),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _evidence_parents(self, record) -> tuple:
        """Lineage parents = the lineage ids carried by the cited evidence."""
        seen: list[str] = []
        for e in record.evidence:
            if e.lineage_id and e.lineage_id not in seen:
                seen.append(e.lineage_id)
        return tuple(seen)

    def _finalize(self, record, view: RecommendationSourceView, *,
                  created_at: str):
        rid = record.recommendation_id
        parents = self._evidence_parents(record)
        report = self.gate.evaluate(record=record, parents=tuple(parents), requires_lineage=True)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_recommendation_lineage(
            rid, parents=parents, kind=record.kind, scope=record.scope, created_at=created_at))
        self.audit.append("recommendation_created",
                          {"recommendation_id": rid, "kind": record.kind,
                           "lineage_id": node.lineage_id, "n_parents": len(parents)},
                          created_at=created_at)
        version = RecommendationVersion.compute(record.state_signature(), None)
        record = replace(record, version=version, lineage_id=node.lineage_id,
                         audit_state=self.audit.head)
        self.audit.append("version_changed", {"recommendation_id": rid, "version": version,
                                              "reason": f"{record.kind}_generated"},
                          created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        self.registry.register(RecommendationRegistryRecord(
            recommendation_id=rid, kind=record.kind, scope=record.scope,
            subject_id=record.subject_id, priority_level=record.priority.level, version=version,
            lineage_id=node.lineage_id, audit_state=record.audit_state,
            content_signature_value=record.state_signature()))
        self.audit.append("recommendation_registered", {"recommendation_id": rid, "version": version},
                          created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        return record
