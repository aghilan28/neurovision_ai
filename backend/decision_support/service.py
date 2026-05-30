"""Decision Support service facade (V2-P6 public entry point).

Orchestrates the decision-support workflow for a case:

    context -> evidence bundle -> risk context -> prioritization -> guidance
            -> decision-support record

Every artifact is screened by the :class:`DecisionGovernanceGate` (architecture/
quality/context/risk, including the scope guard) and admitted to the
:class:`DecisionRegistry`, which versions it, audits it immutably, and records its
lineage back to the source roots. The service integrates with V2-P5 by embedding
population context from a :class:`PopulationAnalytics` artifact, and it never
mutates source records, diagnoses, or treats.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.decision_support.context.aggregator import ContextAggregator
from backend.decision_support.evidence.bundler import EvidenceBundler
from backend.decision_support.guidance.generator import GuidanceGenerator
from backend.decision_support.prioritization.prioritizer import Prioritizer
from backend.decision_support.registry.registry import DecisionRegistry
from backend.decision_support.reports.builder import DecisionReportBuilder
from backend.decision_support.risk.aggregator import RiskContextAggregator
from backend.decision_support.schemas.decision import (
    DecisionContext,
    DecisionSupportRecord,
    DecisionVersion,
    EvidenceBundle,
    GuidanceRecord,
    PrioritizationRecord,
    RiskContext,
)
from backend.decision_support.validation.validators import (
    DecisionGovernanceGate,
    DecisionValidator,
)
from backend.multi_case_intelligence.lineage.tracker import seed_population_lineage
from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.registry.registry import RegistryEntry
from backend.multi_case_intelligence.schemas.base import ArtifactRef, VersionedArtifact
from backend.multi_case_intelligence.schemas.intelligence import PopulationAnalytics
from backend.multi_case_intelligence.validation.validators import ValidationReport


class DecisionGovernanceViolation(RuntimeError):
    """Raised when a decision artifact fails the governance gate and is refused."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        failed = ", ".join(r.name for r in report.failures)
        super().__init__(f"decision governance gate rejected {report.scope}: {failed}")


@dataclass(frozen=True, slots=True)
class DecisionBundle:
    """The registered artifacts produced for one case (all in the registry)."""

    context: RegistryEntry
    evidence_bundle: RegistryEntry
    risk_context: RegistryEntry
    prioritization: RegistryEntry
    guidance: RegistryEntry
    decision_support: RegistryEntry

    def entries(self) -> tuple[RegistryEntry, ...]:
        return (
            self.context,
            self.evidence_bundle,
            self.risk_context,
            self.prioritization,
            self.guidance,
            self.decision_support,
        )


class DecisionSupportService:
    """Public orchestration surface for the Decision Support Layer."""

    def __init__(
        self,
        population: SourcePopulation,
        *,
        population_analytics: PopulationAnalytics | None = None,
    ) -> None:
        self._population = population
        self._population_analytics = population_analytics
        self.registry = DecisionRegistry()
        self.gate = DecisionGovernanceGate()
        self.validator = DecisionValidator()
        self._context = ContextAggregator()
        self._evidence = EvidenceBundler()
        self._risk = RiskContextAggregator()
        self._prioritizer = Prioritizer()
        self._guidance = GuidanceGenerator()
        self._reports = DecisionReportBuilder()
        # Seed the decision registry's lineage tracker with source provenance.
        seed_population_lineage(self.registry.lineage, population)

    @property
    def population(self) -> SourcePopulation:
        return self._population

    # -- admission --------------------------------------------------------- #
    def _admit(
        self,
        artifact: VersionedArtifact,
        parents: tuple[ArtifactRef, ...],
        *,
        summary: str | None = None,
    ) -> RegistryEntry:
        report = self.gate.evaluate(artifact, parents=parents, requires_lineage=True)
        if not report.passed:
            raise DecisionGovernanceViolation(report)
        return self.registry.register(artifact, parents=parents, summary=summary)

    # -- workflow steps ---------------------------------------------------- #
    def build_context(self, case_id: str) -> RegistryEntry:
        context = self._context.build_context(
            self._population, case_id, population_analytics=self._population_analytics
        )
        return self._admit(context, context.all_source_refs(), summary=f"context for case {case_id}")

    def build_evidence_bundle(self, context_entry: RegistryEntry) -> RegistryEntry:
        context = context_entry.artifact
        assert isinstance(context, DecisionContext)
        bundle = self._evidence.build_bundle(self._population, context)
        return self._admit(bundle, (context_entry.ref,), summary="evidence bundle")

    def build_risk_context(self, context_entry: RegistryEntry) -> RegistryEntry:
        context = context_entry.artifact
        assert isinstance(context, DecisionContext)
        risk = self._risk.build_risk(self._population, context)
        return self._admit(risk, (context_entry.ref,), summary="risk context")

    def build_prioritization(
        self,
        context_entry: RegistryEntry,
        risk_entry: RegistryEntry,
        evidence_entry: RegistryEntry,
    ) -> RegistryEntry:
        prioritization = self._prioritizer.prioritize(
            context_entry.artifact,  # type: ignore[arg-type]
            risk_entry.artifact,  # type: ignore[arg-type]
            evidence_entry.artifact,  # type: ignore[arg-type]
        )
        parents = (context_entry.ref, risk_entry.ref, evidence_entry.ref)
        return self._admit(prioritization, parents, summary="prioritization")

    def build_guidance(
        self,
        context_entry: RegistryEntry,
        risk_entry: RegistryEntry,
        prioritization_entry: RegistryEntry,
    ) -> RegistryEntry:
        guidance = self._guidance.generate(
            self._population,
            context_entry.artifact,  # type: ignore[arg-type]
            risk_entry.artifact,  # type: ignore[arg-type]
            prioritization_entry.artifact,  # type: ignore[arg-type]
        )
        parents = (context_entry.ref, risk_entry.ref, prioritization_entry.ref)
        return self._admit(guidance, parents, summary="guidance")

    def build_decision_support_record(
        self,
        context_entry: RegistryEntry,
        evidence_entry: RegistryEntry,
        risk_entry: RegistryEntry,
        prioritization_entry: RegistryEntry,
        guidance_entry: RegistryEntry,
    ) -> RegistryEntry:
        context: DecisionContext = context_entry.artifact  # type: ignore[assignment]
        prioritization: PrioritizationRecord = prioritization_entry.artifact  # type: ignore[assignment]
        risk: RiskContext = risk_entry.artifact  # type: ignore[assignment]
        guidance: GuidanceRecord = guidance_entry.artifact  # type: ignore[assignment]
        evidence: EvidenceBundle = evidence_entry.artifact  # type: ignore[assignment]

        explanation = (
            f"Case {context.case_ref.id}: review priority '{prioritization.level.value}' "
            f"(score {prioritization.score}); attention band '{risk.band.value}'; "
            f"{evidence.size} evidence item(s); {len(guidance.items)} guidance item(s). "
            "Decision-support only: the clinician remains the decision-maker."
        )
        record = DecisionSupportRecord(
            id=DecisionSupportRecord.mint_id(context.case_ref.id),
            patient_ref=context.patient_ref,
            case_ref=context.case_ref,
            context_ref=context_entry.ref,
            evidence_bundle_ref=evidence_entry.ref,
            risk_context_ref=risk_entry.ref,
            prioritization_ref=prioritization_entry.ref,
            guidance_ref=guidance_entry.ref,
            explanation=explanation,
        )
        parents = (
            context_entry.ref,
            evidence_entry.ref,
            risk_entry.ref,
            prioritization_entry.ref,
            guidance_entry.ref,
        )
        return self._admit(record, parents, summary="decision support record")

    # -- high-level orchestration ----------------------------------------- #
    def process_case(self, case_id: str) -> DecisionBundle:
        """Run the full decision-support workflow for one case."""
        context = self.build_context(case_id)
        evidence = self.build_evidence_bundle(context)
        risk = self.build_risk_context(context)
        prioritization = self.build_prioritization(context, risk, evidence)
        guidance = self.build_guidance(context, risk, prioritization)
        record = self.build_decision_support_record(
            context, evidence, risk, prioritization, guidance
        )
        return DecisionBundle(
            context=context,
            evidence_bundle=evidence,
            risk_context=risk,
            prioritization=prioritization,
            guidance=guidance,
            decision_support=record,
        )

    # -- versioning helper ------------------------------------------------- #
    def version_of(self, entry: RegistryEntry) -> DecisionVersion:
        """Return the :class:`DecisionVersion` record for a registered artifact."""
        history = self.registry.history(entry.ref.kind, entry.ref.id)
        prev = history[-2].content_hash if len(history) >= 2 else None
        return DecisionVersion(
            subject=entry.ref,
            version=entry.version,
            content_hash=entry.content_hash,
            prev_content_hash=prev,
        )

    # -- validation -------------------------------------------------------- #
    def validate(self, *, scope: str = "decision_support") -> ValidationReport:
        return self.validator.validate(self.registry, scope=scope)

    # -- reports ----------------------------------------------------------- #
    def build_decision_report(self, bundle: DecisionBundle) -> RegistryEntry:
        report = self._reports.decision_support_report(
            bundle.decision_support.artifact,  # type: ignore[arg-type]
            bundle.context.artifact,  # type: ignore[arg-type]
            bundle.evidence_bundle.artifact,  # type: ignore[arg-type]
            bundle.risk_context.artifact,  # type: ignore[arg-type]
            bundle.prioritization.artifact,  # type: ignore[arg-type]
            bundle.guidance.artifact,  # type: ignore[arg-type]
        )
        parents = tuple(e.ref for e in bundle.entries())
        return self._admit(report, parents, summary="decision support report")

    # -- traceability ------------------------------------------------------ #
    def trace(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        return self.registry.lineage.trace(ref)

    def roots(self, ref: ArtifactRef) -> tuple[ArtifactRef, ...]:
        return self.registry.lineage.roots(ref)
