"""Final validation for V2-P3 + V2-P4.

Objectively verifies the directive's 19 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v2_p3_p4
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import ast
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from datasets import SyntheticConfig
    from ml.training import TrainingConfig
    from backend.offline_inference import InferenceOrchestrator, PipelineConfig, FakeClock
    from backend.clinical_cases import CaseService, CaseStatus
    from backend.clinical_review import ReviewService
    from backend.clinical_findings import (
        FindingService, FindingRecord, FindingStatus, FindingLifecycleError,
        evidence_spec, validate_identity as validate_finding_id,
    )
    from backend.clinical_knowledge import KnowledgeService, TaxonomyError, RelationshipError
    from backend.clinical_knowledge.identity import validate_identity as validate_knowledge_id

    tmp = tempfile.mkdtemp()
    inference = InferenceOrchestrator(
        PipelineConfig(synthetic=SyntheticConfig(n_patients=14, windows_per_patient=18),
                       training=TrainingConfig(steps=80), model_name="tcn"),
        output_dir=tmp + "/run", clock=FakeClock()).run()

    cs = CaseService(); case = cs.create_case(patient_key="PT-V2P3", case_key="ENC", owner="ops")
    cs.transition(case, CaseStatus.INGESTED, "i"); cs.attach_inference_run(case, tmp + "/run")
    cs.transition(case, CaseStatus.PROCESSING, "p"); cs.transition(case, CaseStatus.READY_FOR_REVIEW, "r")
    study = case.studies[0]; tracker = cs.lineage
    rs = ReviewService(lineage_tracker=tracker)
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()))
    rs.assign(review, assignee="dr.rev"); review, _ = rs.start_session(review)

    fs = FindingService(lineage_tracker=tracker)
    finding = fs.create_finding(
        review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
        record=FindingRecord(observation="GRDA", category="GRDA"),
        evidence_specs=[evidence_spec("inference", study.inference_id, "output-contract@1.0.0",
                                      confidence=0.9, source_lineage_id=study.inference_lineage_id)],
        review_lineage_id=review.lineage_id, inference_lineage_id=study.inference_lineage_id)

    # 1. finding identity
    det = (fs is not None and validate_finding_id(finding.finding_id, "finding")[0])
    check("finding identity system works", det)
    # 2. finding lifecycle (+ forbidden blocked)
    fs.to_draft(finding); fs.submit_for_review(finding); fs.confirm(finding)
    blocked = False
    try:
        fs.transition(finding, FindingStatus.CREATED, "illegal")
    except FindingLifecycleError:
        blocked = True
    check("finding lifecycle works", finding.status == FindingStatus.CONFIRMED and blocked)
    # 3. evidence registry (mandatory evidence)
    no_ev_blocked = False
    try:
        fs.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
                          record=FindingRecord(observation="x"), evidence_specs=[],
                          review_lineage_id=review.lineage_id)
    except ValueError:
        no_ev_blocked = True
    check("evidence registry works", len(finding.evidence) == 1 and no_ev_blocked
          and validate_finding_id(finding.evidence[0].evidence_id, "evidence")[0])
    # 4. interpretation system (separate)
    finding, interp = fs.add_interpretation(finding, text="note",
                                            supporting_evidence=(finding.evidence_ids[0],),
                                            confidence_level="moderate")
    check("interpretation system works",
          interp.interpretation_id in finding.interpretation_ids
          and "interpretation_text" not in finding.to_dict())
    # 5. finding registry
    check("finding registry works", fs.registry.exists(finding.finding_id)
          and finding.finding_id in fs.registry.by_review(review.review_id))
    # 6. finding audit
    flog = fs.audit_log_for(finding.finding_id)
    check("finding audit works", flog.verify() and flog.head == finding.audit_head)
    # 7. finding lineage
    fkinds = {r.kind for r in fs.lineage.chain(finding.lineage_id)}
    check("finding lineage works", fs.lineage.verify_chain(finding.lineage_id)
          and {"finding", "evidence", "review", "inference"}.issubset(fkinds))

    # --- knowledge ---
    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    # 8. terminology
    check("terminology system works", len(ks.terminology.list_terms()) >= 11
          and all(validate_knowledge_id(t, "term")[0] for t in ks.terminology.list_terms()))
    # 9. concept registry
    check("concept registry works", len(ks.concepts.list_concepts()) >= 8
          and ks.concept_by_name("Conformal Coverage") is not None)
    # 10. taxonomy (+ consistency, + rejects bad parent)
    tax_blocked = False
    try:
        ks.taxonomy.add(name="x", category="eeg", parent_id="taxon+" + "0" * 16)
    except TaxonomyError:
        tax_blocked = True
    check("taxonomy system works", ks.taxonomy.check_consistency()[0] and tax_blocked)
    # 11. ontology
    ont_ok, _ = ks.ontology.validate(concepts=ks.concepts, terminology=ks.terminology,
                                     taxonomy=ks.taxonomy, relationships=ks.relationships)
    check("ontology system works", ont_ok)
    # 12. relationship system (+ rejects bad predicate)
    rel_blocked = False
    try:
        ks.relationships.add(subject_id="concept+" + "a" * 16, predicate="bogus",
                             object_id="term+" + "b" * 16)
    except RelationshipError:
        rel_blocked = True
    cid = ks.concept_by_name("Rhythmic Delta Activity")
    rel = ks.link_finding_to_concept(finding_id=finding.finding_id, concept_id=cid,
                                     finding_lineage_id=finding.lineage_id)
    check("relationship system works", rel_blocked and rel.predicate == "finding_describes_concept")
    # 13. knowledge registry
    check("knowledge registry works", ks.registry.latest().version == ks.version)
    # 14. knowledge lineage (relationship node spans both graphs)
    rkinds = {r.kind for r in tracker.chain(rel.lineage_id)}
    check("knowledge lineage works", tracker.verify_chain(rel.lineage_id)
          and {"concept", "finding", "term", "relation"}.issubset(rkinds))

    # 17. V1 lineage intact
    check("V1 lineage remains intact", inference.validation["ok"]
          and any(r.lineage_id == inference.lineage_id for r in tracker.chain(finding.lineage_id)))
    # 18. V2 case/review lineage intact
    check("V2 case/review lineage remains intact",
          cs.lineage.verify_chain(case.lineage_id) and rs.lineage.verify_chain(review.lineage_id)
          and cs.validate(case).ok and rs.validate(review).ok)

    # 16 + 19. boundaries / V0 governance gate
    boundary_ok, detail = _boundary_scan()
    check("V0 governance gates pass (boundaries)", boundary_ok, detail)
    check("no architectural boundary violations", boundary_ok, detail)

    # 15. all tests pass
    check("all tests pass (pytest)", _run_pytest())

    width = max(len(n) for n, _, _ in checks)
    all_ok = True
    print("=== V2-P3 + V2-P4 — Final Validation ===")
    for i, (name, ok, detail) in enumerate(checks, 1):
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {i:2d}. {name.ljust(width)}  {detail}")
    print("\nRESULT:", "ALL CRITERIA SATISFIED" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


def _boundary_scan() -> tuple[bool, str]:
    domain = {"ml", "evaluation", "datasets", "preprocessing", "backend", "monitoring", "deployment"}

    def imports(path):
        found = set()
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.Import):
                for a in n.names:
                    found.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and (n.level or 0) == 0 and n.module:
                found.add(n.module.split(".")[0])
        return found

    violations = []
    for p in (REPO / "ml").rglob("*.py"):
        if "evaluation" in imports(p):
            violations.append(f"ml->evaluation in {p.name}")
    for p in (REPO / "backend").rglob("*.py"):
        if "frontend" in imports(p):
            violations.append(f"backend->frontend in {p.name}")
    for p in (REPO / "frontend").rglob("*.py"):
        leaked = imports(p) & domain
        if leaked:
            violations.append(f"frontend->{sorted(leaked)} in {p.name}")
    return (not violations), ("clean" if not violations else "; ".join(violations))


def _run_pytest() -> bool:
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                              cwd=str(REPO), capture_output=True, text=True, timeout=1200)
        return proc.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
