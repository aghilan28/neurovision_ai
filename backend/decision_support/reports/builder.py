"""Deterministic decision-report construction.

Each builder produces a :class:`DecisionReport` whose ``sections`` are plain,
serializable summaries and whose ``referenced`` field pins the exact artifacts
the report summarizes (so the report is itself traceable).
"""

from __future__ import annotations

from backend.decision_support.schemas.decision import (
    DecisionContext,
    DecisionReport,
    DecisionSupportRecord,
    EvidenceBundle,
    GuidanceRecord,
    PrioritizationRecord,
    RiskContext,
)
from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.validation.validators import ValidationReport


class DecisionReportBuilder:
    """Builds versioned :class:`DecisionReport` artifacts."""

    def decision_support_report(
        self,
        record: DecisionSupportRecord,
        context: DecisionContext,
        evidence_bundle: EvidenceBundle,
        risk_context: RiskContext,
        prioritization: PrioritizationRecord,
        guidance: GuidanceRecord,
    ) -> DecisionReport:
        sections = {
            "patient": record.patient_ref.id,
            "case": record.case_ref.id,
            "priority": {
                "level": prioritization.level.value,
                "score": prioritization.score,
                "reason": prioritization.reason,
            },
            "risk": {
                "band": risk_context.band.value,
                "aggregate": risk_context.aggregate,
                "components": {c.name: c.value for c in risk_context.components},
            },
            "evidence": {
                "count": evidence_bundle.size,
                "ranking": list(evidence_bundle.ranking),
            },
            "guidance": [
                {"category": it.category.value, "message": it.message}
                for it in guidance.items
            ],
            "context_counts": dict(context.counts),
            "context_completeness": dict(context.completeness),
            "explanation": record.explanation,
        }
        refs = (record.ref(),) + record.component_refs()
        return self._build("decision_support", f"Decision support for case {record.case_ref.id}", sections, refs)

    def guidance_report(self, guidance: GuidanceRecord) -> DecisionReport:
        sections = {
            "context": guidance.context_ref.id,
            "items": [
                {
                    "category": it.category.value,
                    "message": it.message,
                    "rationale": it.rationale,
                    "references": [r.id for r in it.references],
                }
                for it in guidance.items
            ],
        }
        return self._build("guidance", f"Guidance for {guidance.context_ref.id}", sections, (guidance.ref(),))

    def evidence_report(self, bundle: EvidenceBundle) -> DecisionReport:
        sections = {
            "context": bundle.context_ref.id,
            "count": bundle.size,
            "items": [
                {
                    "evidence": it.evidence_ref.id,
                    "finding": it.finding_id,
                    "modality": it.modality,
                    "confidence": it.confidence,
                    "abstained": it.abstained,
                    "rank": it.rank,
                }
                for it in bundle.items
            ],
        }
        return self._build("evidence", f"Evidence bundle for {bundle.context_ref.id}", sections, (bundle.ref(),))

    def risk_report(self, risk_context: RiskContext) -> DecisionReport:
        sections = {
            "context": risk_context.context_ref.id,
            "band": risk_context.band.value,
            "aggregate": risk_context.aggregate,
            "components": [
                {"name": c.name, "value": c.value, "basis": c.basis}
                for c in risk_context.components
            ],
        }
        return self._build("risk", f"Risk context for {risk_context.context_ref.id}", sections, (risk_context.ref(),))

    def prioritization_report(self, prioritization: PrioritizationRecord) -> DecisionReport:
        sections = {
            "context": prioritization.context_ref.id,
            "level": prioritization.level.value,
            "score": prioritization.score,
            "reason": prioritization.reason,
            "factors": [
                {"name": f.name, "contribution": f.contribution, "detail": f.detail}
                for f in prioritization.factors
            ],
            "supporting_evidence": [r.id for r in prioritization.supporting_evidence],
        }
        return self._build(
            "prioritization", f"Prioritization for {prioritization.context_ref.id}", sections,
            (prioritization.ref(),),
        )

    def validation_report(
        self, report: ValidationReport, referenced: tuple[ArtifactRef, ...] = ()
    ) -> DecisionReport:
        sections = {
            "scope": report.scope,
            "passed": report.passed,
            "results": [
                {"name": r.name, "passed": r.passed, "detail": r.detail}
                for r in report.results
            ],
        }
        return self._build("validation", f"Validation {report.scope}", sections, referenced)

    def _build(self, report_type: str, title: str, sections: dict, referenced) -> DecisionReport:
        report_id = DecisionReport.mint_id(report_type, title)
        return DecisionReport(
            id=report_id,
            report_type=report_type,
            title=title,
            sections=sections,
            referenced=tuple(referenced),
        )
