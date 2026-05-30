"""End-to-end V2 clinical workflow test (the required deliverable).

Verifies the full chain executes with complete traceability:

    Patient → Case → Study → Inference Artifacts → Review Session →
    Review Lifecycle → Audit Trail → Lineage Trail

and that it is deterministic/reproducible and leaves V1 lineage intact.
"""

from __future__ import annotations

import pytest

from datasets import SyntheticConfig
from ml.training import TrainingConfig
from backend.offline_inference import InferenceOrchestrator, PipelineConfig, FakeClock
from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService, ReviewStatus


def _run_inference(out_dir):
    cfg = PipelineConfig(synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
                         training=TrainingConfig(steps=60), model_name="tcn")
    return InferenceOrchestrator(cfg, output_dir=out_dir, clock=FakeClock()).run()


def _full_workflow(run_dir):
    """Drive the entire Patient→…→Review chain; return (case_service, review_service, case, review)."""
    cs = CaseService()
    case = cs.create_case(patient_key="PT-E2E", case_key="ENC-E2E", owner="dr.kiro")
    cs.transition(case, CaseStatus.INGESTED, "ingest")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "processed")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready")

    rs = ReviewService(lineage_tracker=cs.lineage)
    study = case.studies[0]
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()), owner="dr.kiro")
    rs.assign(review, assignee="dr.rev", priority="urgent")
    cs.transition(case, CaseStatus.UNDER_REVIEW, "review started")
    review, sess = rs.start_session(review)
    review, sess = rs.record_session_activity(
        review, sess, artifacts_viewed=list(study.artifact_refs.keys())[:3],
        reports_viewed=["summary_report"], actions=["reviewed"], notes="confirmed")
    review, sess = rs.end_session(review, sess, outcome="confirmed", notes="done")
    rs.submit_for_confirmation(review)
    rs.complete(review)
    rs.close(review)
    cs.transition(case, CaseStatus.REVIEWED, "review complete")
    return cs, rs, case, review


@pytest.fixture(scope="module")
def workflow(tmp_path_factory):
    out = tmp_path_factory.mktemp("v2_e2e")
    run = _run_inference(str(out / "run"))
    cs, rs, case, review = _full_workflow(str(out / "run"))
    return {"run": run, "cs": cs, "rs": rs, "case": case, "review": review}


def test_full_chain_executes(workflow):
    case, review = workflow["case"], workflow["review"]
    assert case.state.status == CaseStatus.REVIEWED
    assert review.status == ReviewStatus.CLOSED
    assert len(review.sessions) == 1 and not review.sessions[0].is_open


def test_complete_traceability(workflow):
    """A single lineage chain from the review head spans the whole Patient→…→training graph."""
    rs, review, run = workflow["rs"], workflow["review"], workflow["run"]
    chain = rs.lineage.chain(review.lineage_id)
    kinds = {r.kind for r in chain}
    assert {"patient", "case", "study", "inference", "uncertainty", "evaluation",
            "training", "review", "review_session"}.issubset(kinds)
    assert rs.lineage.verify_chain(review.lineage_id)
    # the V1 inference node itself is reachable from the review
    assert any(r.lineage_id == run.lineage_id for r in chain)


def test_audit_trails_intact(workflow):
    cs, rs, case, review = workflow["cs"], workflow["rs"], workflow["case"], workflow["review"]
    case_log = cs.audit_log_for(case.case_id)
    review_log = rs.audit_log_for(review.review_id)
    assert case_log.verify() and review_log.verify()
    assert case_log.head == case.audit_head and review_log.head == review.audit_head


def test_all_validations_pass(workflow):
    cs, rs, case, review = workflow["cs"], workflow["rs"], workflow["case"], workflow["review"]
    assert cs.validate(case).ok
    assert rs.validate(review).ok


def test_v1_inference_still_valid(workflow):
    """V2 must not disturb V1: the V1 inference run's own validation remains intact."""
    run = workflow["run"]
    assert run.validation["ok"] is True


def test_workflow_is_reproducible(tmp_path):
    r1 = _run_inference(str(tmp_path / "a"))
    cs1, rs1, case1, review1 = _full_workflow(str(tmp_path / "a"))
    r2 = _run_inference(str(tmp_path / "b"))
    cs2, rs2, case2, review2 = _full_workflow(str(tmp_path / "b"))
    # content-addressed ids are identical across independent runs
    assert r1.inference_id == r2.inference_id
    assert case1.case_id == case2.case_id and review1.review_id == review2.review_id
    assert case1.version.version == case2.version.version
    assert review1.version.version == review2.version.version
