"""Multi-Case Intelligence service facade (V2-P5 public entry point).

This is the orchestration surface for the intelligence layer. It:

* holds an immutable :class:`SourcePopulation` and captures its baseline digest
  (to later *prove* source truth was not mutated),
* seeds the lineage tracker with the source provenance chain
  (Patient -> Case -> Review -> Finding/Interpretation/Evidence; Knowledge),
* admits every produced artifact through the :class:`GovernanceGate` and the
  :class:`IntelligenceRegistry` (so nothing exists outside the registry, and
  every admission is audited and lineage-tracked),
* exposes high-level operations to build cohorts, analytics, trends, quality
  reports, roll-up reports, and to validate the whole subsystem.

The service never mutates source records.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.multi_case_intelligence.analytics.engine import AnalyticsEngine
from backend.multi_case_intelligence.cohorts.builder import CohortBuilder
from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.quality.analyzer import QualityAnalyzer
from backend.multi_case_intelligence.registry.registry import (
    IntelligenceRegistry,
    RegistryEntry,
)
from backend.multi_case_intelligence.reports.builder import ReportBuilder
from backend.multi_case_intelligence.lineage.tracker import seed_population_lineage
from backend.multi_case_intelligence.schemas.base import (
    ArtifactRef,
    VersionedArtifact,
)
from backend.multi_case_intelligence.schemas.intelligence import (
    Cohort,
    IntelligenceReport,
    SelectionCriteria,
)
from backend.multi_case_intelligence.trends.analyzer import TrendAnalyzer
from backend.multi_case_intelligence.validation.validators import (
    GovernanceGate,
    IntelligenceValidator,
    ValidationReport,
)


class GovernanceViolation(RuntimeError):
    """Raised when an artifact fails the governance gate and is refused."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        failed = ", ".join(r.name for r in report.failures)
        super().__init__(f"governance gate rejected {report.scope}: {failed}")


@dataclass(frozen=True, slots=True)
class IntelligenceBundle:
    """The artifacts produced by a full intelligence run (all registered)."""

    population_analytics: RegistryEntry
    trend: RegistryEntry
    quality: RegistryEntry
    population_report: RegistryEntry


class MultiCaseIntelligenceService:
    """Public orchestration surface for the Multi-Case Intelligence Layer."""

    def __init__(self, population: SourcePopulation) -> None:
        self._population = population
        self._baseline_digest = population.integrity_digest()
        self.registry = IntelligenceRegistry()
        self.gate = GovernanceGate()
        self.validator = IntelligenceValidator()
        self._cohorts = CohortBuilder()
        self._analytics = AnalyticsEngine()
        self._trends = TrendAnalyzer()
        self._quality = QualityAnalyzer()
        self._reports = ReportBuilder()
        self._seed_source_lineage()

    @property
    def population(self) -> SourcePopulation:
        return self._population

    @property
    def baseline_digest(self):
        return self._baseline_digest

    # -- source lineage seeding ------------------------------------------- #
    def _seed_source_lineage(self) -> None:
        """Register the provenance chain of the source population.

        Source artifacts are recorded in the *lineage tracker* only (never the
        intelligence registry). This lets intelligence artifacts resolve their
        roots transitively back to patients.
        """
        seed_population_lineage(self.registry.lineage, self._population)

    def _population_roots(self) -> tuple[ArtifactRef, ...]:
        return tuple(p.ref() for p in self._population.patients)

    # -- admission --------------------------------------------------------- #
    def _admit(
        self,
        artifact: VersionedArtifact,
        parents: tuple[ArtifactRef, ...],
        *,
        requires_lineage: bool = True,
        summary: str | None = None,
    ) -> RegistryEntry:
        report = self.gate.evaluate(
            artifact, parents=parents, requires_lineage=requires_lineage
        )
        if not report.passed:
            raise GovernanceViolation(report)
        return self.registry.register(artifact, parents=parents, summary=summary)

    # -- public operations ------------------------------------------------- #
    def build_cohort(self, criteria: SelectionCriteria) -> RegistryEntry:
        """Build and register a cohort from selection criteria."""
        cohort = self._cohorts.build(self._population, criteria)
        parents = cohort.member_refs or self._population_roots()
        return self._admit(cohort, parents, summary=f"cohort over {criteria.member_kind.value}")

    def build_population_analytics(self, *, scope: str = "population") -> RegistryEntry:
        analytics = self._analytics.analyze_population(self._population, scope=scope)
        return self._admit(analytics, self._population_roots(), summary="population analytics")

    def build_cohort_analytics(self, cohort_entry: RegistryEntry) -> RegistryEntry:
        cohort = cohort_entry.artifact
        assert isinstance(cohort, Cohort)
        analytics = self._analytics.analyze_cohort(self._population, cohort)
        return self._admit(analytics, (cohort_entry.ref,), summary="cohort analytics")

    def build_trend(self, *, scope: str = "population") -> RegistryEntry:
        trend = self._trends.analyze(self._population, scope=scope)
        return self._admit(trend, self._population_roots(), summary="trend analysis")

    def build_quality(self, *, scope: str = "population") -> RegistryEntry:
        quality = self._quality.analyze(self._population, scope=scope)
        return self._admit(quality, self._population_roots(), summary="quality analytics")

    def build_report(
        self,
        report: IntelligenceReport,
        referenced_entries: tuple[RegistryEntry, ...],
    ) -> RegistryEntry:
        parents = tuple(e.ref for e in referenced_entries)
        return self._admit(report, parents, summary=f"{report.report_type} report")

    def build_cohort_report(self, cohort_entry: RegistryEntry) -> RegistryEntry:
        report = self._reports.cohort_report(cohort_entry.artifact)  # type: ignore[arg-type]
        return self.build_report(report, (cohort_entry,))

    def build_analytics_report(self, analytics_entry: RegistryEntry) -> RegistryEntry:
        report = self._reports.analytics_report(analytics_entry.artifact)  # type: ignore[arg-type]
        return self.build_report(report, (analytics_entry,))

    def build_trend_report(self, trend_entry: RegistryEntry) -> RegistryEntry:
        report = self._reports.trend_report(trend_entry.artifact)  # type: ignore[arg-type]
        return self.build_report(report, (trend_entry,))

    def build_quality_report(self, quality_entry: RegistryEntry) -> RegistryEntry:
        report = self._reports.quality_report(quality_entry.artifact)  # type: ignore[arg-type]
        return self.build_report(report, (quality_entry,))

    def build_population_report(
        self,
        analytics_entry: RegistryEntry,
        quality_entry: RegistryEntry,
        trend_entry: RegistryEntry | None = None,
    ) -> RegistryEntry:
        report = self._reports.population_report(
            analytics_entry.artifact,  # type: ignore[arg-type]
            quality_entry.artifact,  # type: ignore[arg-type]
            trend_entry.artifact if trend_entry else None,  # type: ignore[arg-type]
        )
        refs = (analytics_entry, quality_entry) + ((trend_entry,) if trend_entry else ())
        return self.build_report(report, refs)

    def run_full_intelligence(self) -> IntelligenceBundle:
        """Convenience: build population analytics + trend + quality + roll-up."""
        analytics = self.build_population_analytics()
        trend = self.build_trend()
        quality = self.build_quality()
        report = self.build_population_report(analytics, quality, trend)
        return IntelligenceBundle(
            population_analytics=analytics,
            trend=trend,
            quality=quality,
            population_report=report,
        )

    # -- validation -------------------------------------------------------- #
    def validate(self, *, scope: str = "intelligence") -> ValidationReport:
        """Validate the whole subsystem and source immutability."""
        return self.validator.validate(
            self.registry,
            population=self._population,
            baseline_digest=self._baseline_digest,
            scope=scope,
        )

    def validation_report_artifact(self, report: ValidationReport) -> IntelligenceReport:
        """Render a validation report as a (non-registered) report artifact."""
        return self._reports.validation_report(report)

    # -- traceability helpers --------------------------------------------- #
    def trace(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        return self.registry.lineage.trace(ref)

    def roots(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        return self.registry.lineage.roots(ref)
