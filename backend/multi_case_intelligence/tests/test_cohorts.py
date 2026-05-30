"""Cohort framework tests (V2-P5 cohort system)."""

from __future__ import annotations

from backend.multi_case_intelligence.cohorts.builder import CohortBuilder
from backend.multi_case_intelligence.population import PopulationBuilder
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.intelligence import (
    Combinator,
    Criterion,
    SelectionCriteria,
)
from backend.multi_case_intelligence.schemas.source import Patient


def test_finding_cohort_selects_by_category(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.FINDING,
        clauses=(Criterion(field="category", op="eq", value="SZ"),),
        description="seizure findings",
    )
    cohort = builder.build(sample_population, criteria)
    assert cohort.members == ("F1",)
    assert cohort.member_kind == ArtifactKind.FINDING


def test_cohort_members_are_sorted_and_unique(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.FINDING,
        clauses=(Criterion(field="has_evidence", op="eq", value=True),),
    )
    cohort = builder.build(sample_population, criteria)
    assert list(cohort.members) == sorted(cohort.members)
    assert len(set(cohort.members)) == len(cohort.members)
    assert set(cohort.members) == {"F1", "F2", "F4"}


def test_or_combinator(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.FINDING,
        clauses=(
            Criterion(field="category", op="eq", value="SZ"),
            Criterion(field="category", op="eq", value="LPD"),
        ),
        combinator=Combinator.OR,
    )
    cohort = builder.build(sample_population, criteria)
    assert set(cohort.members) == {"F1", "F3"}


def test_numeric_threshold_selection(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.FINDING,
        clauses=(Criterion(field="confidence", op="gte", value=0.8),),
    )
    cohort = builder.build(sample_population, criteria)
    assert set(cohort.members) == {"F1", "F4"}


def test_empty_clause_selects_whole_kind(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(member_kind=ArtifactKind.CASE)
    cohort = builder.build(sample_population, criteria)
    assert set(cohort.members) == {"C1", "C2", "C3", "C4"}


def test_cohort_is_deterministic(sample_population):
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.REVIEW,
        clauses=(Criterion(field="is_finalized", op="eq", value=True),),
    )
    c1 = builder.build(sample_population, criteria)
    c2 = builder.build(sample_population, criteria)
    assert c1.id == c2.id
    assert c1.compute_hash() == c2.compute_hash()


def test_cohort_identity_is_definition_not_membership():
    """Same definition over changed data -> same id, different content hash."""
    builder = CohortBuilder()
    criteria = SelectionCriteria(
        member_kind=ArtifactKind.PATIENT,
        clauses=(Criterion(field="site", op="eq", value="siteA"),),
    )
    pop1 = PopulationBuilder().add_patient(Patient(patient_id="P1", site="siteA")).build()
    pop2 = (
        PopulationBuilder()
        .add_patient(Patient(patient_id="P1", site="siteA"))
        .add_patient(Patient(patient_id="P9", site="siteA"))
        .build()
    )
    c1 = builder.build(pop1, criteria)
    c2 = builder.build(pop2, criteria)
    assert c1.id == c2.id  # same logical cohort definition
    assert c1.compute_hash() != c2.compute_hash()  # different membership result
    assert c1.members == ("P1",)
    assert c2.members == ("P1", "P9")
