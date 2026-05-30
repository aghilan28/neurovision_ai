"""End-to-end V2-P5 + V2-P6 deliverable-chain test.

Proves the full required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Interpretation -> Knowledge
            -> Cohort Intelligence -> Evidence Context -> Decision Support
            -> Guidance -> Audit Trail -> Lineage Trail

and that all cross-version invariants hold (source immutability, governance
gates, audit immutability, lineage to patient roots, reproducibility, and
decision-support scope).
"""

from __future__ import annotations

from backend.decision_support.service import DecisionSupportService
from backend.decision_support.validation.validators import DecisionScopeGuard
from backend.multi_case_intelligence import MultiCaseIntelligenceService
from backend.multi_case_intelligence.schemas.base import ArtifactKind
from backend.multi_case_intelligence.schemas.intelligence import (
    Criterion,
    SelectionCriteria,
)


def test_full_chain_executes_with_traceability(sample_population):
    # --- V2-P5: cohort intelligence over the population --------------------
    mci = MultiCaseIntelligenceService(sample_population)
    cohort = mci.build_cohort(
        SelectionCriteria(
            member_kind=ArtifactKind.FINDING,
            clauses=(Criterion(field="has_evidence", op="eq", value=True),),
            description="findings with evidence",
        )
    )
    intel = mci.run_full_intelligence()
    cohort_analytics = mci.build_cohort_analytics(cohort)

    mci_report = mci.validate()
    assert mci_report.passed, mci_report.summary()

    # --- V2-P6: decision support, integrating population intelligence ------
    ds = DecisionSupportService(
        sample_population, population_analytics=intel.population_analytics.artifact
    )
    bundles = {case_id: ds.process_case(case_id) for case_id in ("C1", "C2", "C3", "C4")}
    decision_report = ds.build_decision_report(bundles["C3"])

    ds_report = ds.validate()
    assert ds_report.passed, ds_report.summary()

    # --- Traceability: every decision-support record traces to source roots,
    #     always including a patient (knowledge is also a legitimate root since
    #     it is general clinical truth, not derived from a single patient). ----
    source_root_kinds = {ArtifactKind.PATIENT, ArtifactKind.KNOWLEDGE}
    for bundle in bundles.values():
        roots = ds.roots(bundle.decision_support.ref)
        assert roots, "decision support record must trace to a source root"
        root_kinds = {r.kind for r in roots}
        assert root_kinds <= source_root_kinds
        assert ArtifactKind.PATIENT in root_kinds

    # --- The chain links are all present in the C3 decision trace ----------
    trace_kinds = {r.kind for r in ds.trace(bundles["C3"].decision_support.ref)}
    for kind in (
        ArtifactKind.PATIENT,
        ArtifactKind.CASE,
        ArtifactKind.REVIEW,
        ArtifactKind.FINDING,
        ArtifactKind.DECISION_CONTEXT,
        ArtifactKind.EVIDENCE_BUNDLE,
        ArtifactKind.RISK_CONTEXT,
        ArtifactKind.PRIORITIZATION,
        ArtifactKind.GUIDANCE,
    ):
        assert kind in trace_kinds, f"missing {kind} in decision lineage"

    # --- Audit trails are immutable and intact -----------------------------
    assert mci.registry.audit.verify()
    assert ds.registry.audit.verify()
    assert len(mci.registry.audit) > 0
    assert len(ds.registry.audit) > 0

    # --- No source artifact was mutated by either layer --------------------
    assert sample_population.integrity_digest() == mci.baseline_digest
    assert "source_immutability" not in {r.name for r in mci_report.failures}

    # --- Decision-support scope is respected (no diagnosis/treatment) ------
    guard = DecisionScopeGuard()
    for entry in ds.registry.all_versions():
        assert guard.scan_artifact(entry.artifact) == ()

    # --- Reports exist and are registered ----------------------------------
    assert mci.registry.contains(intel.population_report.ref)
    assert mci.registry.contains(cohort_analytics.ref)
    assert ds.registry.contains(decision_report.ref)


def test_full_chain_is_reproducible():
    """Two independent runs over identical data produce identical hashes."""
    from conftest import build_sample_population

    def run():
        pop = build_sample_population()
        mci = MultiCaseIntelligenceService(pop)
        intel = mci.run_full_intelligence()
        ds = DecisionSupportService(pop, population_analytics=intel.population_analytics.artifact)
        bundle = ds.process_case("C3")
        return (
            intel.population_analytics.content_hash,
            intel.trend.content_hash,
            intel.quality.content_hash,
            bundle.decision_support.content_hash,
            bundle.guidance.content_hash,
            mci.registry.audit.head_hash,
            ds.registry.audit.head_hash,
        )

    assert run() == run()


def test_decision_support_does_not_modify_intelligence_or_source(sample_population):
    mci = MultiCaseIntelligenceService(sample_population)
    intel = mci.run_full_intelligence()
    analytics_hash_before = intel.population_analytics.content_hash

    ds = DecisionSupportService(
        sample_population, population_analytics=intel.population_analytics.artifact
    )
    ds.process_case("C1")

    # The intelligence artifact embedded as population context is unchanged,
    # and the source population digest is unchanged.
    assert intel.population_analytics.content_hash == analytics_hash_before
    assert sample_population.integrity_digest() == mci.baseline_digest
