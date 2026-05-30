"""Deterministic, process-oriented guidance generation (V2-P6).

Guidance items are assembled from a fixed set of controlled templates that speak
only about the *review process* (completing reviews, attaching evidence,
consulting knowledge, completing interpretation, allocating attention by
uncertainty). The templates never reference diagnoses, treatments, medications,
or clinical orders; the decision scope guard re-checks every generated message.
"""

from __future__ import annotations

from backend.clinical_review.models.domain import ReviewStatus
from backend.multi_case_intelligence.population import PopulationView

from ..identity import mint_guidance
from ..models.domain import (
    DecisionContext, GuidanceCategory, GuidanceItem, GuidanceRecord, PrioritizationRecord, RiskContext,
)

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}


class GuidanceGenerator:
    """Builds explainable, process-only :class:`GuidanceRecord` artifacts (read-only)."""

    def build(self, population: PopulationView, context: DecisionContext,
              risk_context: RiskContext, prioritization: PrioritizationRecord) -> GuidanceRecord:
        case_id = context.case_id
        reviews = population.reviews_for_case(case_id)
        findings = population.findings_for_case(case_id)
        unfinalized = [r for r in reviews if r.status not in _FINALIZED_REVIEW]
        missing_interp = [f for f in findings if not f.interpretation_ids]
        thin_evidence = [f for f in findings if len(f.evidence) < 2]
        unknown_categories = sorted({f.record.category for f in findings
                                     if not population.category_is_known(f.record.category)})

        items: list[GuidanceItem] = []

        if unfinalized:
            items.append(GuidanceItem(
                category=GuidanceCategory.REVIEW,
                message=f"{len(unfinalized)} of {len(reviews)} review(s) for this case are not yet "
                        "finalized; consider completing review before sign-off.",
                rationale="Finalized reviews improve completeness and traceability.",
                references=tuple(r.review_id for r in unfinalized)))
        else:
            items.append(GuidanceItem(
                category=GuidanceCategory.REVIEW,
                message="All reviews for this case are finalized.",
                rationale="No outstanding review steps detected.",
                references=tuple(context.review_ids)))

        if missing_interp:
            items.append(GuidanceItem(
                category=GuidanceCategory.INVESTIGATION,
                message=f"{len(missing_interp)} finding(s) do not yet have an interpretation; "
                        "consider completing interpretation to close the record.",
                rationale="Interpretation completeness is a V2 quality dimension.",
                references=tuple(f.finding_id for f in missing_interp)))

        if thin_evidence:
            items.append(GuidanceItem(
                category=GuidanceCategory.EVIDENCE,
                message=f"{len(thin_evidence)} finding(s) rest on a single evidence item; consider "
                        "whether additional supporting evidence is available for review.",
                rationale="Corroborating evidence strengthens the reviewable record.",
                references=tuple(f.finding_id for f in thin_evidence)))

        if unknown_categories:
            items.append(GuidanceItem(
                category=GuidanceCategory.KNOWLEDGE,
                message="Knowledge is not linked for finding categories: "
                        f"{', '.join(unknown_categories)}; consider consulting the knowledge layer.",
                rationale="Linked knowledge supports interpretation of the pattern.",
                references=tuple(context.concept_ids)))

        top = max(risk_context.components, key=lambda c: (c.value, c.name)) if risk_context.components else None
        top_txt = f" The largest contributor is {top.name} ({top.value})." if top else ""
        items.append(GuidanceItem(
            category=GuidanceCategory.RISK,
            message=f"Uncertainty/attention band is '{risk_context.band.value}' "
                    f"(aggregate {risk_context.aggregate}); review priority is "
                    f"'{prioritization.level.value}'.{top_txt} Allocate reviewer attention accordingly.",
            rationale="Higher uncertainty/incompleteness warrants closer human review.",
            references=(risk_context.risk_id, prioritization.priority_id)))

        ident = mint_guidance(context.context_id)
        return GuidanceRecord(guidance_id=ident.id, context_id=context.context_id, items=tuple(items))
