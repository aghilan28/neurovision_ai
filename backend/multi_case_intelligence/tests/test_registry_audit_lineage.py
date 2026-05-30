"""Registry, audit, and lineage tests (V2-P5 governance substrate)."""

from __future__ import annotations

from dataclasses import replace

from backend.multi_case_intelligence.audit.log import IntelligenceAuditLog
from backend.multi_case_intelligence.registry.registry import IntelligenceRegistry
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.events import AuditAction
from backend.multi_case_intelligence.service import MultiCaseIntelligenceService


def test_audit_log_chain_verifies():
    log = IntelligenceAuditLog()
    from backend.multi_case_intelligence.schemas.base import ArtifactRef

    ref = ArtifactRef(kind=ArtifactKind.REPORT, id="r1", content_hash="h", version=1)
    log.record(AuditAction.CREATE, ref, "created")
    log.record(AuditAction.REGISTER, ref, "registered")
    assert len(log) == 2
    assert log.verify() is True


def test_audit_log_tamper_is_detected():
    log = IntelligenceAuditLog()
    from backend.multi_case_intelligence.schemas.base import ArtifactRef

    ref = ArtifactRef(kind=ArtifactKind.REPORT, id="r1", content_hash="h", version=1)
    log.record(AuditAction.CREATE, ref, "created")
    log.record(AuditAction.REGISTER, ref, "registered")
    # Tamper with an earlier entry's summary.
    log._entries[0] = replace(log._entries[0], summary="forged")
    assert log.verify() is False


def test_registry_versioning_is_idempotent_then_increments(sample_population):
    svc = MultiCaseIntelligenceService(sample_population)
    e1 = svc.build_population_analytics()
    # Re-running identical analytics over identical data is idempotent (v1).
    e1b = svc.build_population_analytics()
    assert e1b.version == 1
    assert e1b.content_hash == e1.content_hash
    assert svc.registry.latest(ArtifactKind.ANALYTICS, e1.ref.id).version == 1


def test_registry_increments_version_when_data_changes(sample_population):
    from conftest import build_sample_population

    svc = MultiCaseIntelligenceService(sample_population)
    e1 = svc.build_population_analytics()
    assert e1.version == 1
    # A second analytics over a *different* population yields v2 of same id...
    # simulate by registering analytics computed from a changed population into
    # the same registry/service is not possible (service is bound to one pop),
    # so we assert version semantics at the registry level directly.
    from backend.multi_case_intelligence.analytics.engine import AnalyticsEngine

    bigger = build_sample_population()
    # remove a finding to change content but keep the same scope/id
    analytics_changed = AnalyticsEngine().analyze_population(bigger, scope="population")
    # same logical id (scope "population"), but we force different content:
    forced = replace(analytics_changed, blocks=analytics_changed.blocks[:1])
    reg: IntelligenceRegistry = svc.registry
    entry2 = reg.register(forced, parents=svc._population_roots())
    assert entry2.ref.id == e1.ref.id
    assert entry2.version == 2


def test_no_artifact_exists_outside_registry(sample_population):
    svc = MultiCaseIntelligenceService(sample_population)
    bundle = svc.run_full_intelligence()
    for entry in (bundle.population_analytics, bundle.trend, bundle.quality, bundle.population_report):
        assert svc.registry.contains(entry.ref)
        # every registered artifact has an audit event and lineage record
        assert svc.registry.audit.for_subject(entry.ref)
        assert svc.registry.lineage.get(entry.ref) is not None


def test_lineage_resolves_to_patient_roots(sample_population):
    svc = MultiCaseIntelligenceService(sample_population)
    analytics = svc.build_population_analytics()
    roots = svc.roots(analytics.ref)
    assert {r.kind for r in roots} == {ArtifactKind.PATIENT}
    assert {r.id for r in roots} == {"P1", "P2", "P3"}


def test_cohort_lineage_traces_full_chain(sample_population):
    from backend.multi_case_intelligence.schemas.intelligence import (
        Criterion,
        SelectionCriteria,
    )

    svc = MultiCaseIntelligenceService(sample_population)
    crit = SelectionCriteria(
        member_kind=ArtifactKind.FINDING,
        clauses=(Criterion(field="finding_id", op="eq", value="F1"),),
    )
    cohort = svc.build_cohort(crit)
    trace_kinds = {r.kind for r in svc.trace(cohort.ref)}
    # F1 -> R1 -> C1 -> P1
    assert ArtifactKind.FINDING in trace_kinds
    assert ArtifactKind.REVIEW in trace_kinds
    assert ArtifactKind.CASE in trace_kinds
    assert ArtifactKind.PATIENT in trace_kinds
