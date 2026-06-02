"""MultiCaseIntelligenceService — the governed orchestration hub for V2-P5.

Generates *intelligence* (cohorts, population analytics, trends, quality reports,
summary reports) over a :class:`PopulationView` of real clinical aggregates,
without ever mutating source truth. Every artifact is produced through one
governed path: governance gate → lineage node (parented by the source nodes) →
immutable audit event → content-addressed version → registry sync.

It shares the platform's single ``ml.lineage.LineageTracker`` (the one used by the
case/review/finding/knowledge services) so a single ``verify_chain`` from any
intelligence node spans back to the patient roots.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .population import PopulationView
from .models.domain import (
    Cohort, CohortDefinition, CohortKind, PopulationAnalytics, Trend, QualityReport,
    IntelligenceReport, IntelVersion, IntelRegistryRecord, artifact_id_of,
)
from .identity import mint_report
from .cohorts import CohortBuilder
from .analytics import AnalyticsEngine
from .trends import TrendAnalyzer
from .quality import QualityAnalyzer
from .audit import make_intelligence_audit_log
from .lineage import make_intel_lineage
from .registry import IntelligenceRegistry
from .validation.validators import GovernanceGate, IntelligenceValidator
from .reports import (
    build_cohort_report, build_analytics_report, build_trend_report, build_quality_report,
    build_population_report, build_validation_report, build_registry_report,
)


class MultiCaseIntelligenceService:
    """Stateful service: registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[IntelligenceRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or IntelligenceRegistry()
        self.audit = make_intelligence_audit_log()
        self.gate = GovernanceGate()
        self.validator = IntelligenceValidator()
        self._cohorts = CohortBuilder()
        self._analytics = AnalyticsEngine()
        self._trends = TrendAnalyzer()
        self._quality = QualityAnalyzer()

    # --- public operations ----------------------------------------------------
    def build_cohort(self, population: PopulationView, definition: CohortDefinition,
                     created_at: str = DETERMINISTIC_EPOCH) -> Cohort:
        cohort = self._cohorts.build(population, definition)
        parents = self._cohort_parents(population, cohort)
        return self._finalize(cohort, "cohort", parents, scope=f"cohort:{cohort.cohort_id}",
                              reason="cohort_built", created_at=created_at)

    def build_population_analytics(self, population: PopulationView, *, scope: str = "population",
                                   created_at: str = DETERMINISTIC_EPOCH) -> PopulationAnalytics:
        analytics = self._analytics.analyze_population(population, scope=scope)
        return self._finalize(analytics, "analytics", self._population_parents(population),
                              scope=scope, reason="analytics_built", created_at=created_at)

    def build_cohort_analytics(self, population: PopulationView, cohort: Cohort,
                               created_at: str = DETERMINISTIC_EPOCH) -> PopulationAnalytics:
        analytics = self._analytics.analyze_cohort(population, cohort)
        parents = (cohort.lineage_id,) if cohort.lineage_id else self._population_parents(population)
        return self._finalize(analytics, "analytics", parents, scope=analytics.scope,
                              reason="cohort_analytics_built", created_at=created_at)

    def build_trend(self, population: PopulationView, *, scope: str = "population",
                    created_at: str = DETERMINISTIC_EPOCH) -> Trend:
        trend = self._trends.analyze(population, scope=scope)
        return self._finalize(trend, "trend", self._population_parents(population),
                              scope=scope, reason="trend_built", created_at=created_at)

    def build_quality(self, population: PopulationView, *, scope: str = "population",
                      created_at: str = DETERMINISTIC_EPOCH) -> QualityReport:
        quality = self._quality.analyze(population, scope=scope)
        return self._finalize(quality, "quality", self._population_parents(population),
                              scope=scope, reason="quality_built", created_at=created_at)

    def build_population_summary(self, analytics: PopulationAnalytics, trend: Trend,
                                 quality: QualityReport, *, scope: str = "population",
                                 created_at: str = DETERMINISTIC_EPOCH) -> IntelligenceReport:
        sections = build_population_report(analytics, trend, quality)
        ident = mint_report("population", scope)
        report = IntelligenceReport(
            report_id=ident.id, report_type="population", scope=scope, sections=sections,
            references=(analytics.analytics_id, trend.trend_id, quality.quality_id))
        parents = tuple(p for p in (analytics.lineage_id, trend.lineage_id, quality.lineage_id) if p)
        return self._finalize(report, "intel_report", parents, scope=scope,
                              reason="population_summary_built", created_at=created_at)

    def run_full_intelligence(self, population: PopulationView,
                              created_at: str = DETERMINISTIC_EPOCH) -> dict:
        """Build population analytics + trend + quality + a summary report."""
        analytics = self.build_population_analytics(population, created_at=created_at)
        trend = self.build_trend(population, created_at=created_at)
        quality = self.build_quality(population, created_at=created_at)
        summary = self.build_population_summary(analytics, trend, quality, created_at=created_at)
        return {"analytics": analytics, "trend": trend, "quality": quality, "summary": summary}

    # --- validation + reports -------------------------------------------------
    def validate(self, artifact, kind: str, *, population: Optional[PopulationView] = None,
                 baseline_digest=None):
        return self.validator.validate(artifact=artifact, kind=kind, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage,
                                       population=population, baseline_digest=baseline_digest)

    def reports(self, *, analytics=None, trend=None, quality=None, cohort=None) -> dict:
        out: dict = {"registry_report": build_registry_report(self.registry)}
        if cohort is not None:
            out["cohort_report"] = build_cohort_report(cohort)
        if analytics is not None:
            out["analytics_report"] = build_analytics_report(analytics)
        if trend is not None:
            out["trend_report"] = build_trend_report(trend)
        if quality is not None:
            out["quality_report"] = build_quality_report(quality)
        if analytics is not None and trend is not None and quality is not None:
            out["population_report"] = build_population_report(analytics, trend, quality)
        return out

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _artifact_id(self, artifact) -> str:
        return artifact_id_of(artifact)

    def _finalize(self, artifact, kind: str, parents: tuple, *, scope: str, reason: str,
                  created_at: str):
        artifact_id = self._artifact_id(artifact)
        # 1. governance gate (architecture/quality/context/risk) before admission
        gate_report = self.gate.evaluate(artifact=artifact, kind=kind, parents=tuple(parents),
                                         requires_lineage=True)
        self.gate.raise_if_failed(gate_report)
        # 2. lineage node parented by the source nodes
        node = self.lineage.record(make_intel_lineage(kind, artifact_id, parents=parents,
                                                      scope=scope, created_at=created_at))
        # 3. immutable audit: creation
        self.audit.append(f"{kind}_created",
                          {"artifact_id": artifact_id, "scope": scope, "lineage_id": node.lineage_id},
                          created_at=created_at)
        # 4. content-addressed version (idempotent on identical content)
        version = IntelVersion.compute(artifact.state_signature(), None)
        finalized = replace(artifact, version=version, lineage_id=node.lineage_id,
                            audit_state=self.audit.head)
        # 5. audit: version + registry
        self.audit.append("version_changed", {"artifact_id": artifact_id, "version": version,
                                              "reason": reason}, created_at=created_at)
        finalized = replace(finalized, audit_state=self.audit.head)
        self.registry.register(IntelRegistryRecord(
            artifact_id=artifact_id, artifact_kind=kind, scope=scope, version=version,
            lineage_id=node.lineage_id, audit_state=finalized.audit_state,
            content_signature_value=artifact.state_signature()))
        self.audit.append(f"{kind}_registered", {"artifact_id": artifact_id, "version": version},
                          created_at=created_at)
        finalized = replace(finalized, audit_state=self.audit.head)
        return finalized

    def _population_parents(self, population: PopulationView) -> tuple:
        ids = []
        for c in population.cases:
            if c.lineage_id:
                ids.append(c.lineage_id)
        for f in population.findings:
            if f.lineage_id:
                ids.append(f.lineage_id)
        return tuple(sorted(set(ids)))

    def _cohort_parents(self, population: PopulationView, cohort: Cohort) -> tuple:
        kind = cohort.definition.member_kind
        members = set(cohort.members)
        ids = []
        if kind is CohortKind.CASE:
            ids = [c.lineage_id for c in population.cases if c.case_id in members and c.lineage_id]
        elif kind is CohortKind.REVIEW:
            ids = [r.lineage_id for r in population.reviews if r.review_id in members and r.lineage_id]
        elif kind is CohortKind.FINDING:
            ids = [f.lineage_id for f in population.findings if f.finding_id in members and f.lineage_id]
        elif kind is CohortKind.INTERPRETATION:
            ids = [i.lineage_id for i in population.interpretations
                   if i.interpretation_id in members and i.lineage_id]
        elif kind is CohortKind.CONCEPT:
            ids = []  # concept lineage nodes are tracked by the knowledge service
        if not ids:
            # An empty cohort still derives from the population it was selected from.
            return self._population_parents(population)
        return tuple(sorted(set(ids)))
