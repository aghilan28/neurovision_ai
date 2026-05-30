"""Decision-support service-level tests (V2-P6)."""

from __future__ import annotations

from backend.decision_support.service import DecisionSupportService
from backend.multi_case_intelligence import MultiCaseIntelligenceService
from backend.multi_case_intelligence.schemas.base import ArtifactKind


def test_process_case_produces_full_bundle(sample_population):
    ds = DecisionSupportService(sample_population)
    bundle = ds.process_case("C3")
    # Every component is registered.
    for entry in bundle.entries():
        assert ds.registry.contains(entry.ref)
        assert ds.registry.audit.for_subject(entry.ref)
        assert ds.registry.lineage.get(entry.ref) is not None


def test_decision_support_record_links_all_components(sample_population):
    ds = DecisionSupportService(sample_population)
    bundle = ds.process_case("C3")
    rec = bundle.decision_support.artifact
    assert rec.context_ref == bundle.context.ref
    assert rec.evidence_bundle_ref == bundle.evidence_bundle.ref
    assert rec.risk_context_ref == bundle.risk_context.ref
    assert rec.prioritization_ref == bundle.prioritization.ref
    assert rec.guidance_ref == bundle.guidance.ref


def test_decision_lineage_traces_to_patient(sample_population):
    ds = DecisionSupportService(sample_population)
    bundle = ds.process_case("C3")
    roots = ds.roots(bundle.decision_support.ref)
    assert {r.kind for r in roots} == {ArtifactKind.PATIENT}
    assert {r.id for r in roots} == {"P2"}
    trace_kinds = {r.kind for r in ds.trace(bundle.decision_support.ref)}
    assert ArtifactKind.DECISION_CONTEXT in trace_kinds
    assert ArtifactKind.GUIDANCE in trace_kinds
    assert ArtifactKind.PATIENT in trace_kinds


def test_decision_validation_passes(sample_population):
    ds = DecisionSupportService(sample_population)
    for case_id in ("C1", "C2", "C3", "C4"):
        ds.process_case(case_id)
    report = ds.validate()
    assert report.passed, report.summary()
    names = {r.name for r in report.results}
    assert "decision_scope_integrity" in names
    assert "audit_integrity" in names
    assert "lineage_integrity" in names


def test_decision_version_record(sample_population):
    ds = DecisionSupportService(sample_population)
    bundle = ds.process_case("C3")
    dv = ds.version_of(bundle.decision_support)
    assert dv.version == 1
    assert dv.prev_content_hash is None
    assert dv.content_hash == bundle.decision_support.content_hash


def test_reproducible_across_instances(sample_population):
    from conftest import build_sample_population

    a = DecisionSupportService(sample_population)
    b = DecisionSupportService(build_sample_population())
    ba = a.process_case("C3")
    bb = b.process_case("C3")
    assert ba.decision_support.content_hash == bb.decision_support.content_hash
    assert ba.guidance.content_hash == bb.guidance.content_hash
    assert a.registry.audit.head_hash == b.registry.audit.head_hash


def test_integration_with_intelligence_population_context(sample_population):
    mci = MultiCaseIntelligenceService(sample_population)
    analytics = mci.build_population_analytics()
    ds = DecisionSupportService(sample_population, population_analytics=analytics.artifact)
    bundle = ds.process_case("C1")
    ctx = bundle.context.artifact
    assert ctx.population_context  # population intelligence embedded
    assert ds.validate().passed
