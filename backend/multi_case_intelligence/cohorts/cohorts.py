"""Deterministic cohort construction over a population (V2-P5).

``CohortBuilder`` projects each source aggregate into a flat, serializable
*normalized view*, evaluates the cohort's :class:`CohortDefinition` against that
view, and returns a :class:`Cohort` whose membership is the sorted set of matching
ids. The projection is the only place that knows the field vocabulary available to
selection criteria, keeping criteria explainable and stable.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.clinical_review.models.domain import ReviewStatus

from ..identity import mint_cohort
from ..models.domain import Cohort, CohortCriterion, CohortDefinition, CohortKind
from ..population import PopulationView, finding_confidence

_FINALIZED_REVIEW = {ReviewStatus.COMPLETED, ReviewStatus.CLOSED, ReviewStatus.ARCHIVED}


def normalize(record: Any, kind: CohortKind, population: PopulationView) -> Mapping[str, Any]:
    """Project a source aggregate into the flat field vocabulary for selection."""
    if kind is CohortKind.CASE:
        return {
            "case_id": record.case_id, "patient_id": record.patient_id,
            "status": record.state.status.value, "n_studies": len(record.studies),
            "n_reviews": len(population.reviews_for_case(record.case_id)),
            "n_findings": len(population.findings_for_case(record.case_id)),
        }
    if kind is CohortKind.REVIEW:
        return {
            "review_id": record.review_id, "case_id": record.case_id,
            "status": record.status.value, "reviewer": record.reviewer,
            "is_finalized": record.status in _FINALIZED_REVIEW,
            "n_sessions": len(record.sessions), "n_assignments": len(record.assignments),
        }
    if kind is CohortKind.FINDING:
        conf = finding_confidence(record)
        return {
            "finding_id": record.finding_id, "case_id": record.case_id,
            "review_id": record.review_id, "status": record.status.value,
            "category": record.record.category, "observation": record.record.observation,
            "n_evidence": len(record.evidence), "n_interpretations": len(record.interpretation_ids),
            "has_interpretation": len(record.interpretation_ids) > 0,
            "confidence": conf, "known_category": population.category_is_known(record.record.category),
        }
    if kind is CohortKind.INTERPRETATION:
        return {
            "interpretation_id": record.interpretation_id, "finding_id": record.finding_id,
            "confidence_level": record.confidence_level,
            "n_supporting_evidence": len(record.supporting_evidence),
            "n_concept_refs": len(record.concept_refs),
        }
    if kind is CohortKind.CONCEPT:
        return {
            "concept_id": record.concept_id, "name": record.name, "status": record.status,
            "n_related_terms": len(record.related_terms),
            "n_evidence_links": len(record.evidence_links), "taxon_id": record.taxon_id,
        }
    raise ValueError(f"cannot normalize cohort kind {kind!r}")


def _evaluate(view: Mapping[str, Any], crit: CohortCriterion) -> bool:
    present = crit.field in view
    value = view.get(crit.field)
    op = crit.op
    if op == "exists":
        return present and value is not None
    if not present:
        return False
    if op == "eq":
        return value == crit.value
    if op == "ne":
        return value != crit.value
    if op == "in":
        return value in (crit.value or ())
    if op == "contains":
        try:
            return crit.value in value  # type: ignore[operator]
        except TypeError:
            return False
    if op in ("gte", "lte"):
        if value is None or crit.value is None:
            return False
        try:
            return value >= crit.value if op == "gte" else value <= crit.value
        except TypeError:
            return False
    raise ValueError(f"unhandled op {op!r}")  # pragma: no cover


def _matches(view: Mapping[str, Any], definition: CohortDefinition) -> bool:
    if not definition.criteria:
        return True
    results = (_evaluate(view, c) for c in definition.criteria)
    return all(results) if definition.combinator == "and" else any(results)


class CohortBuilder:
    """Builds :class:`Cohort` artifacts from a population (read-only)."""

    _COLLECTION = {
        CohortKind.CASE: lambda p: p.cases,
        CohortKind.REVIEW: lambda p: p.reviews,
        CohortKind.FINDING: lambda p: p.findings,
        CohortKind.INTERPRETATION: lambda p: p.interpretations,
        CohortKind.CONCEPT: lambda p: p.concepts,
    }
    _ID_ATTR = {
        CohortKind.CASE: "case_id", CohortKind.REVIEW: "review_id",
        CohortKind.FINDING: "finding_id", CohortKind.INTERPRETATION: "interpretation_id",
        CohortKind.CONCEPT: "concept_id",
    }

    def build(self, population: PopulationView, definition: CohortDefinition) -> Cohort:
        kind = definition.member_kind
        records = self._COLLECTION[kind](population)
        id_attr = self._ID_ATTR[kind]
        members = sorted(
            getattr(r, id_attr) for r in records if _matches(normalize(r, kind, population), definition)
        )
        ident = mint_cohort(kind.value, [c.to_dict() for c in definition.criteria], definition.combinator)
        return Cohort(cohort_id=ident.id, definition=definition, members=tuple(members))
