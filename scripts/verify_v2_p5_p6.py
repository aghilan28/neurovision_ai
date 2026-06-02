"""Final validation for V2-P5 + V2-P6.

Objectively verifies the directive's 20 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v2_p5_p6
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from backend.clinical_cases import CaseService
    from backend.clinical_review import ReviewService
    from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
    from backend.clinical_knowledge import KnowledgeService
    from backend.multi_case_intelligence import (
        MultiCaseIntelligenceService, CohortDefinition, CohortCriterion, CohortKind,
    )
    from backend.decision_support import DecisionSupportService, DecisionScopeGuard

    # --- build a small multi-case population through the real services --------
    cs = CaseService()
    ks = KnowledgeService(lineage_tracker=cs.lineage).seed_default_knowledge()
    rs = ReviewService(lineage_tracker=cs.lineage)
    fs = FindingService(lineage_tracker=cs.lineage)
    from backend.multi_case_intelligence import PopulationBuilder
    pb = PopulationBuilder()

    cases = {}
    for pid, cat, conf, finalize in [("PT1", "LPD", 0.9, True), ("PT2", "GRDA", 0.3, False),
                                     ("PT3", "unknown_pattern", 0.8, False)]:
        case = cs.create_case(patient_key=pid, case_key=f"ENC-{pid}", owner="ops")
        review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                                  study_id=None, inference_lineage_id=None, artifact_refs=())
        rs.assign(review, assignee="dr"); review, _ = rs.start_session(review)
        if finalize:
            rs.submit_for_confirmation(review); rs.complete(review)
        finding = fs.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=None,
                record=FindingRecord(observation=cat, category=cat),
                evidence_specs=[evidence_spec("inference", f"inf-{pid}", "output-contract@1.0.0", confidence=conf)],
                review_lineage_id=review.lineage_id)
        cases[pid] = case
        pb.add_case(case).add_review(review).add_finding(finding)
    pb.add_knowledge_service(ks)
    pop = pb.build()
    baseline = pop.integrity_digest()

    # --- V2-P5 ---------------------------------------------------------------
    mci = MultiCaseIntelligenceService(lineage_tracker=cs.lineage)
    cohort = mci.build_cohort(pop, CohortDefinition(member_kind=CohortKind.FINDING,
                              criteria=(CohortCriterion("category", "eq", "LPD"),)))
    check("1. Cohort system works", cohort.size == 1 and mci.registry.exists(cohort.cohort_id))
    res = mci.run_full_intelligence(pop)
    an, tr, q = res["analytics"], res["trend"], res["quality"]
    check("2. Population analytics works", an.block("finding").count == 3)
    check("3. Trend analysis works", any(s.metric == "finding_status_progression" for s in tr.series))
    check("4. Quality analytics works", len(q.metrics) >= 6 and all(0 <= m.value <= 1 for m in q.metrics))
    check("5. Intelligence registry works",
          mci.registry.exists(an.analytics_id) and len(mci.registry.list_artifacts()) >= 5)
    check("6. Intelligence audit works", mci.audit.verify() and len(mci.audit) > 0)
    check("7. Intelligence lineage works",
          mci.lineage.verify_chain(an.lineage_id)
          and "patient" in {r.kind for r in mci.lineage.chain(an.lineage_id)})

    # --- V2-P6 ---------------------------------------------------------------
    ds = DecisionSupportService(lineage_tracker=cs.lineage)
    bundles = {pid: ds.process_case(pop, cases[pid].case_id, population_analytics=an) for pid in cases}
    b1 = bundles["PT2"]
    check("8. Context aggregation works", b1.context.counts["findings"] == 1)
    check("9. Evidence bundling works",
          b1.evidence_bundle.size == 1 and set(b1.evidence_bundle.ranking) == set(b1.context.evidence_ids))
    check("10. Prioritization works",
          abs(round(sum(f.contribution for f in b1.prioritization.factors), 6) - b1.prioritization.score) < 1e-9)
    check("11. Guidance system works",
          any(it.category.value == "risk" for it in b1.guidance.items))
    check("12. Risk context works",
          len(b1.risk_context.components) == 7
          and abs(round(sum(c.value for c in b1.risk_context.components) / 7, 6) - b1.risk_context.aggregate) < 1e-9)
    check("13. Decision registry works",
          ds.registry.exists(b1.decision_support.record_id) and len(ds.registry.list_artifacts()) >= 6)
    check("14. Decision lineage works",
          ds.lineage.verify_chain(b1.decision_support.lineage_id)
          and "patient" in {r.kind for r in ds.lineage.chain(b1.decision_support.lineage_id)})

    # 15. all tests pass
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_multi_case_intelligence.py", "tests/test_decision_support.py",
         "tests/test_v2_p5_p6_e2e.py", "tests/test_boundaries.py"],
        cwd=str(REPO), capture_output=True, text=True)
    check("15. All tests pass", proc.returncode == 0, proc.stdout.strip().splitlines()[-1] if proc.stdout else "")

    # 16. governance gates pass for every produced artifact
    gate_ok = True
    for art, kind in [(cohort, "cohort"), (an, "analytics"), (tr, "trend"), (q, "quality")]:
        gate_ok = gate_ok and mci.gate.evaluate(artifact=art, kind=kind, parents=(an.lineage_id,)).ok
    for art, kind in zip(b1.artifacts(),
                         ["decision_context", "evidence_bundle", "risk_context", "prioritization",
                          "guidance", "decision_support"]):
        gate_ok = gate_ok and ds.gate.evaluate(artifact=art, kind=kind, parents=(b1.context.lineage_id,)).ok
    check("16. V0 governance gates pass", gate_ok)

    # 17/18. V1 + V2 lineage intact (source chains verify; source digest unchanged)
    fid_chain = mci.lineage.verify_chain(pop.findings[0].lineage_id)
    check("17. V1 lineage remains intact", fid_chain and pop.integrity_digest() == baseline)
    check("18. V2 case/review/finding/knowledge lineage remains intact",
          all(mci.lineage.verify_chain(c.lineage_id) for c in pop.cases)
          and pop.integrity_digest() == baseline)

    # 19. no architectural boundary violations (delegated to the boundary tests)
    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("19. No architectural boundary violations", bnd.returncode == 0)

    # 20. no recommendation exceeds decision-support scope
    guard = DecisionScopeGuard()
    scope_clean = all(guard.scan_artifact(a) == () for b in bundles.values() for a in b.artifacts())
    check("20. No recommendation exceeds decision-support scope", scope_clean)

    print("\nV2-P5 + V2-P6 FINAL VALIDATION")
    print("=" * 60)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)
    print("=" * 60)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
