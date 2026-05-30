"""Deterministic cohort construction.

``CohortBuilder`` projects each source record into a flat, serializable
*normalized view*, evaluates the cohort's :class:`SelectionCriteria` against that
view, and emits a :class:`Cohort` artifact whose membership is the sorted set of
matching ids. The projection is the only place that knows the field vocabulary
available to selection criteria, which keeps criteria explainable and stable.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.base import ArtifactRef
from backend.multi_case_intelligence.schemas.intelligence import (
    Cohort,
    Combinator,
    Criterion,
    SelectionCriteria,
)
from backend.multi_case_intelligence.schemas.source import (
    ClinicalCase,
    Evidence,
    Finding,
    Interpretation,
    Knowledge,
    Patient,
    Review,
    Study,
)


def normalize(record: object) -> Mapping[str, Any]:
    """Project a source record into the flat field vocabulary for selection.

    The vocabulary is deliberately small and explicit so that cohort criteria are
    self-documenting and reproducible.
    """
    if isinstance(record, Patient):
        return {"patient_id": record.patient_id, "site": record.site}
    if isinstance(record, Study):
        return {
            "study_id": record.study_id,
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "montage": record.montage,
        }
    if isinstance(record, ClinicalCase):
        return {
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "site": record.site,
            "status": record.status,
            "ordinal": record.ordinal,
        }
    if isinstance(record, Review):
        return {
            "review_id": record.review_id,
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "status": record.status.value,
            "reviewer_role": record.reviewer_role,
            "completeness": record.completeness,
            "is_finalized": record.is_finalized,
        }
    if isinstance(record, Evidence):
        sig = record.signal
        return {
            "evidence_id": record.evidence_id,
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "finding_id": record.finding_id,
            "modality": record.modality,
            "confidence": None if sig is None else sig.confidence,
            "abstained": None if sig is None else sig.abstained,
        }
    if isinstance(record, Finding):
        sig = record.signal
        risk = record.risk
        return {
            "finding_id": record.finding_id,
            "review_id": record.review_id,
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "category": record.category.value,
            "confidence": None if sig is None else sig.confidence,
            "empirical_coverage": None if sig is None else sig.empirical_coverage,
            "calibration_error": None if sig is None else sig.calibration_error,
            "abstained": None if sig is None else sig.abstained,
            "n_evidence": len(record.evidence_ids),
            "has_evidence": len(record.evidence_ids) > 0,
            "inference_risk": None if risk is None else risk.inference_risk,
            "coverage_risk": None if risk is None else risk.coverage_risk,
            "calibration_risk": None if risk is None else risk.calibration_risk,
        }
    if isinstance(record, Interpretation):
        return {
            "interpretation_id": record.interpretation_id,
            "finding_id": record.finding_id,
            "case_id": record.case_id,
            "patient_id": record.patient_id,
            "completeness": record.completeness,
        }
    if isinstance(record, Knowledge):
        return {
            "knowledge_id": record.knowledge_id,
            "topic": record.topic,
            "finding_category": None
            if record.finding_category is None
            else record.finding_category.value,
            "n_references": len(record.references),
        }
    raise TypeError(f"cannot normalize record of type {type(record)!r}")


def _evaluate_clause(view: Mapping[str, Any], clause: Criterion) -> bool:
    present = clause.field in view
    value = view.get(clause.field)
    op = clause.op
    if op == "exists":
        return present and value is not None
    if not present:
        return False
    if op == "eq":
        return value == clause.value
    if op == "ne":
        return value != clause.value
    if op == "in":
        return value in (clause.value or ())
    if op == "contains":
        try:
            return clause.value in value  # type: ignore[operator]
        except TypeError:
            return False
    if op in ("gte", "lte"):
        if value is None or clause.value is None:
            return False
        try:
            return value >= clause.value if op == "gte" else value <= clause.value
        except TypeError:
            return False
    raise ValueError(f"unhandled op {op!r}")  # pragma: no cover - guarded by Criterion


def _matches(view: Mapping[str, Any], criteria: SelectionCriteria) -> bool:
    if not criteria.clauses:
        return True  # an empty criteria set selects the whole population of the kind
    results = (_evaluate_clause(view, c) for c in criteria.clauses)
    if criteria.combinator is Combinator.AND:
        return all(results)
    return any(results)


class CohortBuilder:
    """Builds :class:`Cohort` artifacts from a source population (read-only)."""

    def build(
        self,
        population: SourcePopulation,
        criteria: SelectionCriteria,
        *,
        schema_version: str = "v2.p5.1",
    ) -> Cohort:
        """Construct a cohort of ``criteria.member_kind`` members.

        Membership is the sorted set of ids whose normalized view satisfies the
        criteria. The cohort id is content-addressed by ``(kind, criteria,
        members)`` so identical definitions over identical data share an id.
        """
        records = population.collection(criteria.member_kind)
        selected: list[ArtifactRef] = []
        for rec in records:
            if _matches(normalize(rec), criteria):
                selected.append(rec.ref())  # type: ignore[attr-defined]
        selected.sort(key=lambda r: r.id)
        member_ids = tuple(r.id for r in selected)
        # The cohort's *logical identity* is its definition (kind + criteria),
        # NOT its membership result. Re-running the same definition over changed
        # data therefore yields the same id with new content -> a new version.
        cohort_id = Cohort.mint_id(
            criteria.member_kind.value,
            [(c.field, c.op, c.value) for c in criteria.clauses],
            criteria.combinator.value,
        )
        return Cohort(
            id=cohort_id,
            schema_version=schema_version,
            member_kind=criteria.member_kind,
            criteria=criteria,
            members=member_ids,
            member_refs=tuple(selected),
        )
