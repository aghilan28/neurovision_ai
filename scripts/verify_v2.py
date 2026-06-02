"""Final validation for V2-P1 + V2-P2.

Objectively verifies the directive's 17 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v2
"""

from __future__ import annotations

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
    from backend.clinical_cases import (
        CaseService, CaseStatus, LifecycleError, mint_identity, validate_identity, IdentityError,
    )
    from backend.clinical_review import ReviewService, ReviewStatus, ReviewLifecycleError

    tmp = tempfile.mkdtemp()
    inference = InferenceOrchestrator(
        PipelineConfig(synthetic=SyntheticConfig(n_patients=14, windows_per_patient=18),
                       training=TrainingConfig(steps=80), model_name="tcn"),
        output_dir=tmp + "/run", clock=FakeClock()).run()

    cs = CaseService()
    case = cs.create_case(patient_key="PT-V2", case_key="ENC-V2", owner="clinical-ops")

    # 1. Case identity system works
    try:
        det = (mint_identity("patient", {"patient_key": "X"}).id
               == mint_identity("patient", {"patient_key": "X"}).id)
        future_blocked = False
        try:
            mint_identity("finding", {"review_id": "review+0000000000000000", "finding_key": "F"})
        except IdentityError:
            future_blocked = True
        check("case identity system works",
              validate_identity(case.case_id, "case")[0] and det and future_blocked)
    except Exception as exc:
        check("case identity system works", False, repr(exc))

    # 2. Case lifecycle works (valid advances + forbidden blocked)
    try:
        cs.transition(case, CaseStatus.INGESTED, "ingest")
        blocked = False
        try:
            cs.transition(case, CaseStatus.CLOSED, "illegal")
        except LifecycleError:
            blocked = True
        check("case lifecycle works", case.state.status == CaseStatus.INGESTED and blocked)
    except Exception as exc:
        check("case lifecycle works", False, repr(exc))

    # attach the V1 inference + advance to review-ready
    cs.attach_inference_run(case, tmp + "/run")
    cs.transition(case, CaseStatus.PROCESSING, "proc")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready")
    study = case.studies[0]

    # 3. Case registry works
    check("case registry works",
          cs.registry.exists(case.case_id) and cs.registry.get(case.case_id).version == case.version.version)
    # 4. Case audit works (tamper-evident)
    clog = cs.audit_log_for(case.case_id)
    check("case audit works", clog.verify() and clog.head == case.audit_head and len(clog) > 0)
    # 5. Case lineage works
    check("case lineage works", cs.lineage.verify_chain(case.lineage_id)
          and any(r.lineage_id == inference.lineage_id for r in cs.lineage.chain(case.lineage_id)))
    # 6. Case validation works
    creport = cs.validate(case)
    check("case validation works", creport.ok and len(creport.checks) == 7)

    # --- review ---
    rs = ReviewService(lineage_tracker=cs.lineage)
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()), owner="clinical-ops")
    rs.assign(review, assignee="dr.rev", priority="urgent")
    review, sess = rs.start_session(review)
    review, sess = rs.record_session_activity(
        review, sess, artifacts_viewed=list(study.artifact_refs.keys())[:3],
        reports_viewed=["summary_report"], actions=["reviewed"], notes="ok")
    review, sess = rs.end_session(review, sess, outcome="confirmed")
    rs.submit_for_confirmation(review); rs.complete(review); rs.close(review)

    # 7. Review lifecycle works
    try:
        blocked = False
        try:
            rs.transition(review, ReviewStatus.CREATED, "illegal")
        except ReviewLifecycleError:
            blocked = True
        check("review lifecycle works", review.status == ReviewStatus.CLOSED and blocked)
    except Exception as exc:
        check("review lifecycle works", False, repr(exc))
    # 8. Review session system works
    check("review session system works",
          len(review.sessions) == 1 and not review.sessions[0].is_open
          and review.sessions[0].review_outcome == "confirmed")
    # 9. Assignment system works
    check("assignment system works",
          review.reviewer == "dr.rev" and len(review.assignments) == 1
          and review.assignments[0].priority == "urgent")
    # 10. Review tracking works
    tr = rs.tracking(review)
    check("review tracking works", tr["is_complete"] and tr["progress"] == 1.0)
    # 11. Review registry works
    check("review registry works",
          rs.registry.exists(review.review_id) and review.review_id in rs.registry.by_case(case.case_id))
    # 12. Review audit works
    rlog = rs.audit_log_for(review.review_id)
    check("review audit works", rlog.verify() and rlog.head == review.audit_head)
    # 13. Review lineage works (chain reaches case + inference)
    rkinds = {r.kind for r in rs.lineage.chain(review.lineage_id)}
    check("review lineage works", rs.lineage.verify_chain(review.lineage_id)
          and {"review", "review_session", "case", "study", "inference"}.issubset(rkinds))

    # 16. Version 1 lineage remains intact (inference still valid + node reachable)
    check("V1 lineage remains intact", inference.validation["ok"]
          and any(r.lineage_id == inference.lineage_id for r in rs.lineage.chain(review.lineage_id)))

    # 15 + 17. boundaries / V0 governance gate
    boundary_ok, detail = _boundary_scan()
    check("V0 governance gates pass (boundaries)", boundary_ok, detail)
    check("no architectural boundary violations", boundary_ok, detail)

    # 14. All tests pass
    check("all tests pass (pytest)", _run_pytest())

    width = max(len(n) for n, _, _ in checks)
    all_ok = True
    print("=== V2-P1 + V2-P2 — Final Validation ===")
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
    for p in (REPO / "preprocessing").rglob("*.py"):
        leaked = imports(p) & (domain - {"preprocessing"})
        if leaked:
            violations.append(f"preprocessing->{sorted(leaked)} in {p.name}")
    return (not violations), ("clean" if not violations else "; ".join(violations))


def _run_pytest() -> bool:
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                              cwd=str(REPO), capture_output=True, text=True, timeout=900)
        return proc.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
