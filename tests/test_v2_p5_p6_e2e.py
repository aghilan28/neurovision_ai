"""End-to-end V2-P5 + V2-P6 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Interpretation -> Knowledge
            -> Cohort Intelligence -> Evidence Context -> Decision Support
            -> Guidance -> Audit Trail -> Lineage Trail

over the real V2 aggregates, and that all cross-version invariants hold (source
immutability, governance, audit immutability, lineage to patient, reproducibility,
and decision-support scope).
"""

from __future__ import annotations

from backend.multi_case_intelligence import (
    MultiCaseIntelligenceService, CohortDefinition, CohortCriterion, CohortKind,
)
from backend.decision_support import DecisionSupportService, DecisionScopeGuard

from tests._p5p6_helpers import build_multicase


def test_full_chain_executes_with_traceability():
    mc = build_multicase()
    tracker = mc.cs.lineage  # single shared platform lineage tracker

    # --- V2-P5: cohort intelligence over the population --------------------
    mci = MultiCaseIntelligenceService(lineage_tracker=tracker)
    baseline = mc.population.integrity_digest()
    cohort = mci.build_cohort(mc.population, CohortDefinition(
        member_kind=CohortKind.FINDING, criteria=(CohortCriterion("category", "eq", "LPD"),)))
    cohort_analytics = mci.build_cohort_analytics(mc.population, cohort)
    res = mci.run_full_intelligence(mc.population)

    for art, kind in [(cohort, "cohort"), (cohort_analytics, "analytics"),
                      (res["analytics"], "analytics"), (res["trend"], "trend"),
                      (res["quality"], "quality"), (res["summary"], "intel_report")]:
        assert mci.validate(art, kind, population=mc.population, baseline_digest=baseline).ok

    # --- V2-P6: decision support, integrating population intelligence ------
    ds = DecisionSupportService(lineage_tracker=tracker)
    bundles = {cid: ds.process_case(mc.population, mc.cases[cid].case_id,
                                    population_analytics=res["analytics"])
               for cid in ("C1", "C2", "C3")}
    kinds = ["decision_context", "evidence_bundle", "risk_context", "prioritization",
             "guidance", "decision_support"]
    for bundle in bundles.values():
        for art, kind in zip(bundle.artifacts(), kinds):
            assert ds.validate(art, kind, population=mc.population, baseline_digest=baseline).ok

    # --- traceability: every decision-support record reaches a patient -----
    for bundle in bundles.values():
        chain_kinds = {r.kind for r in tracker.chain(bundle.decision_support.lineage_id)}
        for k in ("patient", "case", "review", "finding", "decision_context",
                  "evidence_bundle", "risk_context", "prioritization", "guidance", "decision_support"):
            assert k in chain_kinds, f"missing {k} in decision lineage"
        assert tracker.verify_chain(bundle.decision_support.lineage_id)

    # --- audit trails immutable + intact -----------------------------------
    assert mci.audit.verify() and ds.audit.verify()
    assert len(mci.audit) > 0 and len(ds.audit) > 0

    # --- no source artifact was mutated ------------------------------------
    assert mc.population.integrity_digest() == baseline

    # --- decision-support scope respected (no diagnosis/treatment) ---------
    guard = DecisionScopeGuard()
    for bundle in bundles.values():
        for art in bundle.artifacts():
            assert guard.scan_artifact(art) == ()

    # --- everything registered ---------------------------------------------
    assert mci.registry.exists(cohort.cohort_id)
    assert all(ds.registry.exists(b.decision_support.record_id) for b in bundles.values())


def test_full_chain_is_reproducible():
    def run():
        mc = build_multicase()
        mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
        res = mci.run_full_intelligence(mc.population)
        ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
        bundle = ds.process_case(mc.population, mc.cases["C1"].case_id,
                                 population_analytics=res["analytics"])
        return (res["analytics"].state_signature(), res["trend"].state_signature(),
                res["quality"].state_signature(), bundle.decision_support.state_signature(),
                mci.audit.head, ds.audit.head)

    assert run() == run()


def test_decision_support_does_not_mutate_intelligence_or_source():
    mc = build_multicase()
    mci = MultiCaseIntelligenceService(lineage_tracker=mc.cs.lineage)
    an = mci.build_population_analytics(mc.population)
    before = an.state_signature()
    baseline = mc.population.integrity_digest()
    ds = DecisionSupportService(lineage_tracker=mc.cs.lineage)
    ds.process_case(mc.population, mc.cases["C1"].case_id, population_analytics=an)
    assert an.state_signature() == before
    assert mc.population.integrity_digest() == baseline
