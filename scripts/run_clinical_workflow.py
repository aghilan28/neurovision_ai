"""Run the V2 clinical workflow end to end (V2-P1 + V2-P2).

Drives the full required deliverable with complete traceability:

    Patient → Case → Study → Inference Artifacts → Review Session →
    Review Lifecycle → Audit Trail → Lineage Trail

It first produces a real V1 offline-inference run, then builds a Case around it,
attaches the inference as a Study, runs a structured Review (assign → session →
complete → close), and prints the audit + lineage trails. Scripts may import any
layer; this is the only place the V1 and V2 backend subsystems are composed.

    python -m scripts.run_clinical_workflow
"""

from __future__ import annotations

import argparse
import tempfile

from datasets import SyntheticConfig
from ml.training import TrainingConfig
from backend.offline_inference import InferenceOrchestrator, PipelineConfig
from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService, ReviewStatus


def run(argv=None) -> dict:
    p = argparse.ArgumentParser(description="Run the NeuroVision AI V2 clinical workflow end to end.")
    p.add_argument("--patients", type=int, default=12)
    p.add_argument("--windows-per-patient", type=int, default=18)
    p.add_argument("--model", default="tcn", choices=["simple_cnn", "eegnet", "tcn"])
    p.add_argument("--steps", type=int, default=80)
    p.add_argument("--reviewer", default="dr.reviewer")
    p.add_argument("--run-dir", default=None)
    args = p.parse_args(argv)

    run_dir = args.run_dir or (tempfile.mkdtemp() + "/inference_run")

    # 1) V1 offline inference (raw EEG -> registered intelligence artifacts)
    cfg = PipelineConfig(synthetic=SyntheticConfig(n_patients=args.patients,
                                                   windows_per_patient=args.windows_per_patient),
                         training=TrainingConfig(steps=args.steps), model_name=args.model)
    inference = InferenceOrchestrator(cfg, output_dir=run_dir).run()
    print("=== V1 Offline Inference ===")
    print(f"inference_id : {inference.inference_id}")
    print(f"lineage_id   : {inference.lineage_id}  (validation ok: {inference.validation['ok']})")

    # 2) Clinical Case Foundation (V2-P1)
    cs = CaseService()
    case = cs.create_case(patient_key="PT-DEID-DEMO", case_key="ENC-DEMO", owner="clinical-ops")
    cs.transition(case, CaseStatus.INGESTED, "EEG ingested")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "intelligence computed")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready for review")
    study = case.studies[0]
    print("\n=== V2-P1 Clinical Case ===")
    print(f"patient_id   : {case.patient_id}")
    print(f"case_id      : {case.case_id}  status={case.state.status.value}")
    print(f"study_id     : {study.study_id}  -> inference {study.inference_id}")

    # 3) Clinical Review Workflow (V2-P2) — shares the case's lineage tracker
    rs = ReviewService(lineage_tracker=cs.lineage)
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()), owner="clinical-ops")
    rs.assign(review, assignee=args.reviewer, priority="urgent", reason="triage")
    cs.transition(case, CaseStatus.UNDER_REVIEW, "review started")
    review, sess = rs.start_session(review)
    review, sess = rs.record_session_activity(
        review, sess, artifacts_viewed=list(study.artifact_refs.keys())[:3],
        reports_viewed=["summary_report", "coverage_report"],
        actions=["reviewed_calibration", "reviewed_coverage"], notes="calibrated; coverage reliable")
    review, sess = rs.end_session(review, sess, outcome="confirmed", notes="pattern confirmed")
    rs.submit_for_confirmation(review)
    rs.complete(review)
    rs.close(review)
    cs.transition(case, CaseStatus.REVIEWED, "review complete")

    print("\n=== V2-P2 Clinical Review ===")
    print(f"review_id    : {review.review_id}  status={review.status.value}")
    print(f"reviewer     : {review.reviewer}  sessions={len(review.sessions)}")
    tracking = rs.tracking(review)
    print(f"progress     : {tracking['progress']:.2f}  milestones={tracking['milestones_reached']}")

    # 4) Trails
    case_ok = cs.validate(case).ok
    review_ok = rs.validate(review).ok
    chain = rs.lineage.chain(review.lineage_id)
    chain_kinds = sorted(set(r.kind for r in chain))
    print("\n=== Trails ===")
    print(f"case validation   : {'OK' if case_ok else 'FAILED'} (7 checks)")
    print(f"review validation : {'OK' if review_ok else 'FAILED'} (7 checks)")
    print(f"audit (case)      : verified={cs.audit_log_for(case.case_id).verify()} "
          f"events={len(cs.audit_log_for(case.case_id))}")
    print(f"audit (review)    : verified={rs.audit_log_for(review.review_id).verify()} "
          f"events={len(rs.audit_log_for(review.review_id))}")
    print(f"lineage chain     : verified={rs.lineage.verify_chain(review.lineage_id)} "
          f"nodes={len(chain)} kinds={chain_kinds}")
    print(f"traceability      : Patient -> Case -> Study -> Inference -> Review -> Session "
          f"({'COMPLETE' if rs.lineage.verify_chain(review.lineage_id) else 'BROKEN'})")

    return {"inference_id": inference.inference_id, "case_id": case.case_id,
            "review_id": review.review_id, "case_ok": case_ok, "review_ok": review_ok,
            "chain_verified": rs.lineage.verify_chain(review.lineage_id)}


if __name__ == "__main__":
    run()
