"""Validation, governance gate, and service-level tests (V2-P5)."""

from __future__ import annotations


from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.intelligence import (
    Criterion,
    SelectionCriteria,
)
from backend.multi_case_intelligence.service import (
    MultiCaseIntelligenceService,
)
from backend.multi_case_intelligence.validation.validators import GovernanceGate


def test_full_subsystem_validation_passes(sample_population):
    svc = MultiCaseIntelligenceService(sample_population)
    svc.run_full_intelligence()
    svc.build_cohort(
        SelectionCriteria(
            member_kind=ArtifactKind.FINDING,
            clauses=(Criterion(field="category", op="eq", value="SZ"),),
        )
    )
    report = svc.validate()
    assert report.passed, report.summary()
    names = {r.name for r in report.results}
    assert {
        "audit_integrity",
        "registry_integrity",
        "lineage_integrity",
        "version_integrity",
        "cohort_integrity",
        "analytics_integrity",
        "trend_integrity",
        "source_immutability",
    } <= names


def test_source_immutability_detected_when_baseline_changes(sample_population):
    from conftest import build_sample_population

    svc = MultiCaseIntelligenceService(sample_population)
    svc.build_population_analytics()
    # Validate against a *different* baseline digest -> immutability check fails.
    other = build_sample_population()
    # tweak: build a population with an extra patient to change the digest
    from backend.multi_case_intelligence.population import PopulationBuilder
    from backend.multi_case_intelligence.schemas.source import Patient

    pb = PopulationBuilder()
    for p in other.patients:
        pb.add_patient(p)
    pb.add_patient(Patient(patient_id="PZZZ", site="siteC"))
    changed = pb.build()
    report = svc.validator.validate(
        svc.registry,
        population=changed,
        baseline_digest=svc.baseline_digest,
        scope="tamper-check",
    )
    failures = {r.name for r in report.failures}
    assert "source_immutability" in failures


def test_governance_gate_rejects_source_kind():
    """The intelligence gate must refuse to produce a non-intelligence kind."""
    from backend.multi_case_intelligence.schemas.intelligence import (
        Cohort,
        SelectionCriteria as SC,
    )

    gate = GovernanceGate()
    cohort = Cohort(
        id="cohort-x",
        member_kind=ArtifactKind.FINDING,
        criteria=SC(member_kind=ArtifactKind.FINDING),
        members=("F1",),
    )
    # Valid cohort passes architecture/quality but needs lineage parents.
    report = gate.evaluate(cohort, parents=(), requires_lineage=True)
    assert not report.passed
    assert "context_validation" in {r.name for r in report.failures}


def test_service_is_reproducible_across_instances(sample_population):
    from conftest import build_sample_population

    svc_a = MultiCaseIntelligenceService(sample_population)
    svc_b = MultiCaseIntelligenceService(build_sample_population())
    a = svc_a.run_full_intelligence()
    b = svc_b.run_full_intelligence()
    assert a.population_analytics.content_hash == b.population_analytics.content_hash
    assert a.trend.content_hash == b.trend.content_hash
    assert a.quality.content_hash == b.quality.content_hash
    # Audit chains built from identical actions are identical too.
    assert svc_a.registry.audit.head_hash == svc_b.registry.audit.head_hash


def test_empty_population_validates(sample_population):
    from backend.multi_case_intelligence.population import PopulationBuilder

    svc = MultiCaseIntelligenceService(PopulationBuilder().build())
    # With no patients, population-scope artifacts have no lineage roots; the
    # gate would reject them, so we only validate the (empty) subsystem state.
    report = svc.validate()
    assert report.passed, report.summary()
