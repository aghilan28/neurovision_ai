"""DecisionSupportService — the governed orchestration hub for V2-P6.

Runs the per-case decision-support workflow:

    context -> evidence bundle -> risk context -> prioritization -> guidance
            -> decision-support record

Every artifact is produced through one governed path: decision governance gate
(architecture/quality/context/risk — risk = the scope guard) → shared-lineage node
parented by its source/context nodes → immutable audit event → content-addressed
version → registry sync. It shares the platform's single ``ml.lineage.LineageTracker``
so a single ``verify_chain`` from any decision node spans back to the patient roots.

It reads the real V2 aggregates via a V2-P5 ``PopulationView`` and never mutates
source, intelligence, diagnoses, or treats. The clinician remains the decision-maker.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ml.lineage import LineageTracker  # allowed: backend -> ml
from backend.multi_case_intelligence.population import PopulationView

from .version import DETERMINISTIC_EPOCH
from .models.domain import (
    DecisionContext, EvidenceBundle, RiskContext, PrioritizationRecord, GuidanceRecord,
    DecisionSupportRecord, DecisionVersion, DecisionRegistryRecord, artifact_id_of, artifact_kind_of,
)
from .identity import mint_decision_support
from .context import ContextAggregator
from .evidence import EvidenceBundler
from .risk import RiskContextAggregator
from .prioritization import Prioritizer
from .guidance import GuidanceGenerator
from .audit import make_decision_audit_log
from .lineage import make_decision_lineage
from .registry import DecisionRegistry
from .validation.validators import DecisionGovernanceGate, DecisionValidator
from .reports import (
    build_evidence_report, build_risk_report, build_prioritization_report, build_guidance_report,
    build_decision_support_report, build_validation_report, build_registry_report,
)


@dataclass(frozen=True)
class DecisionBundle:
    """The registered artifacts produced for one case."""

    context: DecisionContext
    evidence_bundle: EvidenceBundle
    risk_context: RiskContext
    prioritization: PrioritizationRecord
    guidance: GuidanceRecord
    decision_support: DecisionSupportRecord

    def artifacts(self) -> tuple:
        return (self.context, self.evidence_bundle, self.risk_context,
                self.prioritization, self.guidance, self.decision_support)


class DecisionSupportService:
    """Stateful service: registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[DecisionRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or DecisionRegistry()
        self.audit = make_decision_audit_log()
        self.gate = DecisionGovernanceGate()
        self.validator = DecisionValidator()
        self._context = ContextAggregator()
        self._evidence = EvidenceBundler()
        self._risk = RiskContextAggregator()
        self._prioritizer = Prioritizer()
        self._guidance = GuidanceGenerator()

    # --- workflow steps -------------------------------------------------------
    def build_context(self, population: PopulationView, case_id: str, *,
                      population_analytics=None, created_at: str = DETERMINISTIC_EPOCH) -> DecisionContext:
        context = self._context.build(population, case_id, population_analytics=population_analytics)
        parents = self._context_source_parents(population, context)
        return self._finalize(context, parents, case_id=case_id, reason="context_built",
                              created_at=created_at)

    def build_evidence_bundle(self, population: PopulationView, context: DecisionContext,
                              created_at: str = DETERMINISTIC_EPOCH) -> EvidenceBundle:
        bundle = self._evidence.build(population, context)
        return self._finalize(bundle, (context.lineage_id,), case_id=context.case_id,
                              reason="evidence_bundled", created_at=created_at)

    def build_risk_context(self, population: PopulationView, context: DecisionContext,
                           created_at: str = DETERMINISTIC_EPOCH) -> RiskContext:
        risk = self._risk.build(population, context)
        return self._finalize(risk, (context.lineage_id,), case_id=context.case_id,
                              reason="risk_built", created_at=created_at)

    def build_prioritization(self, context: DecisionContext, risk: RiskContext,
                             bundle: EvidenceBundle,
                             created_at: str = DETERMINISTIC_EPOCH) -> PrioritizationRecord:
        pr = self._prioritizer.build(context, risk, bundle)
        parents = tuple(p for p in (context.lineage_id, risk.lineage_id, bundle.lineage_id) if p)
        return self._finalize(pr, parents, case_id=context.case_id, reason="prioritized",
                              created_at=created_at)

    def build_guidance(self, population: PopulationView, context: DecisionContext, risk: RiskContext,
                       prioritization: PrioritizationRecord,
                       created_at: str = DETERMINISTIC_EPOCH) -> GuidanceRecord:
        g = self._guidance.build(population, context, risk, prioritization)
        parents = tuple(p for p in (context.lineage_id, risk.lineage_id, prioritization.lineage_id) if p)
        return self._finalize(g, parents, case_id=context.case_id, reason="guidance_built",
                              created_at=created_at)

    def build_decision_support_record(self, context: DecisionContext, bundle: EvidenceBundle,
                                      risk: RiskContext, prioritization: PrioritizationRecord,
                                      guidance: GuidanceRecord,
                                      created_at: str = DETERMINISTIC_EPOCH) -> DecisionSupportRecord:
        explanation = (
            f"Case {context.case_id}: review priority '{prioritization.level.value}' "
            f"(score {prioritization.score}); attention band '{risk.band.value}'; "
            f"{bundle.size} evidence item(s); {len(guidance.items)} guidance item(s). "
            "Decision-support only: the clinician remains the decision-maker.")
        ident = mint_decision_support(context.context_id)
        record = DecisionSupportRecord(
            record_id=ident.id, case_id=context.case_id, patient_id=context.patient_id,
            context_id=context.context_id, evidence_bundle_id=bundle.bundle_id, risk_id=risk.risk_id,
            prioritization_id=prioritization.priority_id, guidance_id=guidance.guidance_id,
            explanation=explanation)
        parents = tuple(p for p in (context.lineage_id, bundle.lineage_id, risk.lineage_id,
                                    prioritization.lineage_id, guidance.lineage_id) if p)
        return self._finalize(record, parents, case_id=context.case_id,
                              reason="decision_support_built", created_at=created_at)

    def process_case(self, population: PopulationView, case_id: str, *,
                     population_analytics=None, created_at: str = DETERMINISTIC_EPOCH) -> DecisionBundle:
        """Run the full decision-support workflow for one case."""
        context = self.build_context(population, case_id, population_analytics=population_analytics,
                                     created_at=created_at)
        bundle = self.build_evidence_bundle(population, context, created_at=created_at)
        risk = self.build_risk_context(population, context, created_at=created_at)
        prioritization = self.build_prioritization(context, risk, bundle, created_at=created_at)
        guidance = self.build_guidance(population, context, risk, prioritization, created_at=created_at)
        record = self.build_decision_support_record(context, bundle, risk, prioritization, guidance,
                                                    created_at=created_at)
        return DecisionBundle(context=context, evidence_bundle=bundle, risk_context=risk,
                              prioritization=prioritization, guidance=guidance, decision_support=record)

    # --- validation + reports -------------------------------------------------
    def validate(self, artifact, kind: str, *, population: Optional[PopulationView] = None,
                 baseline_digest=None):
        return self.validator.validate(artifact=artifact, kind=kind, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage,
                                       population=population, baseline_digest=baseline_digest)

    def reports(self, bundle: DecisionBundle) -> dict:
        return {
            "registry_report": build_registry_report(self.registry),
            "evidence_report": build_evidence_report(bundle.evidence_bundle),
            "risk_context_report": build_risk_report(bundle.risk_context),
            "prioritization_report": build_prioritization_report(bundle.prioritization),
            "guidance_report": build_guidance_report(bundle.guidance),
            "decision_support_report": build_decision_support_report(
                bundle.decision_support, bundle.context, bundle.evidence_bundle, bundle.risk_context,
                bundle.prioritization, bundle.guidance),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    def version_record(self, artifact) -> DecisionVersion:
        return DecisionVersion(version=getattr(artifact, "version", ""), previous=None,
                               reason="content_addressed", created_at=DETERMINISTIC_EPOCH)

    # --- internals ------------------------------------------------------------
    def _finalize(self, artifact, parents: tuple, *, case_id: str, reason: str, created_at: str):
        artifact_id = artifact_id_of(artifact)
        kind = artifact_kind_of(artifact)
        gate_report = self.gate.evaluate(artifact=artifact, kind=kind, parents=tuple(parents),
                                         requires_lineage=True)
        self.gate.raise_if_failed(gate_report)
        node = self.lineage.record(make_decision_lineage(kind, artifact_id, parents=parents,
                                                        case_id=case_id, created_at=created_at))
        self.audit.append(f"{kind}_created",
                          {"artifact_id": artifact_id, "case_id": case_id, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = DecisionVersion.compute(artifact.state_signature(), None)
        finalized = replace(artifact, version=version, lineage_id=node.lineage_id,
                            audit_state=self.audit.head)
        self.audit.append("version_changed", {"artifact_id": artifact_id, "version": version,
                                              "reason": reason}, created_at=created_at)
        finalized = replace(finalized, audit_state=self.audit.head)
        self.registry.register(DecisionRegistryRecord(
            artifact_id=artifact_id, artifact_kind=kind, case_id=case_id, version=version,
            lineage_id=node.lineage_id, audit_state=finalized.audit_state,
            content_signature_value=artifact.state_signature()))
        self.audit.append(f"{kind}_registered", {"artifact_id": artifact_id, "version": version},
                          created_at=created_at)
        finalized = replace(finalized, audit_state=self.audit.head)
        return finalized

    def _context_source_parents(self, population: PopulationView, context: DecisionContext) -> tuple:
        ids = []
        case = population.case(context.case_id)
        if case is not None and case.lineage_id:
            ids.append(case.lineage_id)
        for r in population.reviews_for_case(context.case_id):
            if r.lineage_id:
                ids.append(r.lineage_id)
        for f in population.findings_for_case(context.case_id):
            if f.lineage_id:
                ids.append(f.lineage_id)
            for i in population.interpretations_for_finding(f.finding_id):
                if i.lineage_id:
                    ids.append(i.lineage_id)
        if not ids:
            return (case.lineage_id,) if (case and case.lineage_id) else ()
        return tuple(sorted(set(ids)))
