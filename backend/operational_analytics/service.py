"""OperationalAnalyticsService — the governed orchestration hub for V3-P5.

Derives **operational analytics** (derived intelligence: metrics, health,
performance, quality, trends, risks) from already-governed upstream artifacts —
events (V3-P1), temporal intelligence (V3-P2), workflows (V3-P3) and the
operational graph (V3-P4) — and admits each through one governed path: governance
gate (architecture/quality/context/risk) -> shared-lineage node parented by the
upstream artifact lineage nodes it derives from -> immutable audit event ->
content-addressed version -> registry sync.

Because each analytics record's lineage parents are upstream nodes (which trace to
the patient), a single ``verify_chain`` spans Patient -> ... -> Event -> Workflow
-> Graph -> Analytics. Analytics is **derived** and never a source of truth.
Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .engine import AnalyticsBuilder
from .models.categories import AnalyticsCategory
from .models.domain import AnalyticsVersion, AnalyticsRegistryRecord
from .models.source import AnalyticsSourceView
from .audit import make_analytics_audit_log
from .lineage import make_analytics_lineage
from .registry import AnalyticsRegistry
from .validation import AnalyticsGovernanceGate, AnalyticsValidator
from .reports import (
    build_metrics_report, build_health_report, build_performance_report, build_quality_report,
    build_trend_report, build_risk_report, build_analytics_summary_report,
    build_validation_report, build_audit_report,
)



class OperationalAnalyticsService:
    """Stateful service: analytics registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[AnalyticsRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or AnalyticsRegistry()
        self.audit = make_analytics_audit_log()
        self.gate = AnalyticsGovernanceGate()
        self.validator = AnalyticsValidator()
        self._builder = AnalyticsBuilder()
        self._view: Optional[AnalyticsSourceView] = None

    # --- source view ----------------------------------------------------------
    def load_sources(self, *, events: Sequence = (), workflows: Sequence = (),
                     graph_registry=None, temporal_analytics=None) -> "OperationalAnalyticsService":
        """Provide the already-governed upstream artifacts to derive analytics from."""
        self._view = AnalyticsSourceView(events=events, workflows=workflows,
                                         graph_registry=graph_registry,
                                         temporal_analytics=temporal_analytics)
        return self

    def view(self) -> AnalyticsSourceView:
        if self._view is None:
            raise RuntimeError("call load_sources(...) before deriving analytics")
        return self._view

    # --- build ----------------------------------------------------------------
    def build_category(self, category: str, *, subject_kind: str = "operational",
                       subject_id: str = "all", scope: Optional[str] = None,
                       created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        record = self._builder.build_category(category, view, subject_kind=subject_kind,
                                               subject_id=subject_id, scope=scope)
        return self._finalize(record, view.all_parents(), reason=f"{category}_built",
                              created_at=created_at)

    def build_operational(self, *, subject_kind: str = "operational", subject_id: str = "all",
                          created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        record = self._builder.build_operational(view, subject_kind=subject_kind,
                                                  subject_id=subject_id)
        return self._finalize(record, view.all_parents(), reason="operational_analytics_built",
                              created_at=created_at)

    def build_all(self, *, subject_kind: str = "operational", subject_id: str = "all",
                  created_at: str = DETERMINISTIC_EPOCH) -> dict:
        """Build + admit every analytics category plus the operational summary."""
        out: dict = {}
        for category in (AnalyticsCategory.METRICS, AnalyticsCategory.HEALTH,
                         AnalyticsCategory.PERFORMANCE, AnalyticsCategory.QUALITY,
                         AnalyticsCategory.TREND, AnalyticsCategory.RISK):
            out[category] = self.build_category(category, subject_kind=subject_kind,
                                                subject_id=subject_id, created_at=created_at)
        out[AnalyticsCategory.OPERATIONAL] = self.build_operational(
            subject_kind=subject_kind, subject_id=subject_id, created_at=created_at)
        return out

    # --- validation + reports -------------------------------------------------
    def validate(self, record):
        return self.validator.validate(record=record, registry=self.registry,
                                        audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, records: Sequence) -> dict:
        records = list(records)
        return {
            "analytics_summary_report": build_analytics_summary_report(records),
            "metrics_report": build_metrics_report(records),
            "health_report": build_health_report(records),
            "performance_report": build_performance_report(records),
            "trend_report": build_trend_report(records),
            "risk_report": build_risk_report(records),
            "audit_report": build_audit_report(self.audit),
        }

    def quality_report(self, records: Sequence) -> dict:
        return build_quality_report(list(records))

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, record, parents: tuple, *, reason: str, created_at: str):
        aid = record.analytics_id
        report = self.gate.evaluate(record=record, parents=tuple(parents), requires_lineage=True)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_analytics_lineage(
            aid, parents=parents, category=record.category, scope=record.scope,
            created_at=created_at))
        self.audit.append("analytics_created",
                          {"analytics_id": aid, "category": record.category,
                           "lineage_id": node.lineage_id, "n_parents": len(parents)},
                          created_at=created_at)
        version = AnalyticsVersion.compute(record.state_signature(), None)
        record = replace(record, version=version, lineage_id=node.lineage_id,
                         audit_state=self.audit.head)
        self.audit.append("version_changed", {"analytics_id": aid, "version": version,
                                              "reason": reason}, created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        self.registry.register(AnalyticsRegistryRecord(
            analytics_id=aid, category=record.category, scope=record.scope,
            subject_id=record.subject_id, version=version, lineage_id=node.lineage_id,
            audit_state=record.audit_state, content_signature_value=record.state_signature()))
        self.audit.append("analytics_registered", {"analytics_id": aid, "version": version},
                          created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        return record
