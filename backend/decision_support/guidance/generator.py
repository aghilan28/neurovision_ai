"""Deterministic, process-oriented guidance generation.

Guidance items are assembled from a fixed set of controlled templates that speak
only about the *review process* (completing reviews, attaching evidence,
consulting knowledge, completing interpretation, allocating attention by
uncertainty). The templates never reference diagnoses, treatments, medications,
or clinical orders; the decision scope guard re-checks every generated message.
"""

from __future__ import annotations

from backend.decision_support.schemas.decision import (
    DecisionContext,
    GuidanceCategory,
    GuidanceItem,
    GuidanceRecord,
    PrioritizationRecord,
    RiskContext,
)
from backend.multi_case_intelligence.population.snapshot import SourcePopulation


class GuidanceGenerator:
    """Builds explainable :class:`GuidanceRecord` artifacts (read-only)."""

    def generate(
        self,
        population: SourcePopulation,
        context: DecisionContext,
        risk_context: RiskContext,
        prioritization: PrioritizationRecord,
        *,
        schema_version: str = "v2.p6.1",
    ) -> GuidanceRecord:
        case_id = context.case_ref.id
        reviews = population.reviews_for_case(case_id)
        findings = population.findings_for_case(case_id)
        unfinalized = [r for r in reviews if not r.is_finalized]
        missing_interp = [
            f for f in findings if not population.interpretations_for_finding(f.finding_id)
        ]
        missing_evidence = [f for f in findings if not f.evidence_ids]

        categories = {f.category for f in findings}
        knowledge_categories = {
            k.finding_category for k in population.knowledge if k.finding_category is not None
        }
        missing_knowledge = sorted(
            (c.value for c in (categories - knowledge_categories)),
        )

        items: list[GuidanceItem] = []

        # --- Review guidance ------------------------------------------------ #
        if unfinalized:
            items.append(
                GuidanceItem(
                    category=GuidanceCategory.REVIEW,
                    message=(
                        f"{len(unfinalized)} of {len(reviews)} review(s) for this case "
                        "are not yet finalized; consider completing review before sign-off."
                    ),
                    rationale="Finalized reviews improve traceability and completeness.",
                    references=tuple(r.ref() for r in unfinalized),
                )
            )
        else:
            items.append(
                GuidanceItem(
                    category=GuidanceCategory.REVIEW,
                    message="All reviews for this case are finalized.",
                    rationale="No outstanding review steps detected.",
                    references=context.review_refs,
                )
            )

        # --- Investigation guidance (interpretation completeness) ----------- #
        if missing_interp:
            items.append(
                GuidanceItem(
                    category=GuidanceCategory.INVESTIGATION,
                    message=(
                        f"{len(missing_interp)} finding(s) do not yet have an interpretation; "
                        "consider completing interpretation to close the record."
                    ),
                    rationale="Interpretation completeness is a V2 quality dimension.",
                    references=tuple(f.ref() for f in missing_interp),
                )
            )

        # --- Evidence guidance ---------------------------------------------- #
        if missing_evidence:
            items.append(
                GuidanceItem(
                    category=GuidanceCategory.EVIDENCE,
                    message=(
                        f"{len(missing_evidence)} finding(s) have no linked evidence; "
                        "consider attaching supporting evidence so the record is reviewable."
                    ),
                    rationale="Every finding should be backed by inspectable evidence.",
                    references=tuple(f.ref() for f in missing_evidence),
                )
            )

        # --- Knowledge guidance --------------------------------------------- #
        if missing_knowledge:
            items.append(
                GuidanceItem(
                    category=GuidanceCategory.KNOWLEDGE,
                    message=(
                        "Knowledge is not linked for finding categories: "
                        f"{', '.join(missing_knowledge)}; consider consulting the knowledge layer."
                    ),
                    rationale="Linked knowledge supports interpretation of the IIC.",
                    references=context.knowledge_refs,
                )
            )

        # --- Risk guidance (always present) --------------------------------- #
        top = max(risk_context.components, key=lambda c: (c.value, c.name)) if risk_context.components else None
        top_txt = f" The largest contributor is {top.name} ({top.value})." if top else ""
        items.append(
            GuidanceItem(
                category=GuidanceCategory.RISK,
                message=(
                    f"Uncertainty/attention band is '{risk_context.band.value}' "
                    f"(aggregate {risk_context.aggregate}); review priority is "
                    f"'{prioritization.level.value}'.{top_txt} Allocate reviewer attention accordingly."
                ),
                rationale="Higher uncertainty/incompleteness warrants closer human review.",
                references=(risk_context.ref(), prioritization.ref()),
            )
        )

        guidance_id = GuidanceRecord.mint_id(context.id)
        return GuidanceRecord(
            id=guidance_id,
            schema_version=schema_version,
            context_ref=context.ref(),
            items=tuple(items),
        )
