"""End-to-end V2-P3 + V2-P4 test (the required deliverable).

Verifies the full chain executes with complete traceability:

    Patient → Case → Study → Review → Evidence → Finding → Interpretation →
    Knowledge Context → Audit Trail → Lineage Trail

and that it is reproducible and leaves V1 and V2-P1/P2 lineage intact.
"""

from __future__ import annotations

import pytest

from datasets import SyntheticConfig
from ml.training import TrainingConfig
from backend.offline_inference import InferenceOrchestrator, PipelineConfig, FakeClock
from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService


def _build(run_dir):
    cs = CaseService()
    case = cs.create_case(patient_key="PT-E2E2", case_key="ENC-E2E2", owner="dr")
    cs.transition(case, CaseStatus.INGESTED, "i")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "p")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "r")
    study = case.studies[0]
    tracker = cs.lineage

    rs = ReviewService(lineage_tracker=tracker)
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()))
    rs.assign(review, assignee="dr.rev")
    review, sess = rs.start_session(review)
    cs.transition(case, CaseStatus.UNDER_REVIEW, "rev")

    fs = FindingService(lineage_tracker=tracker)
    finding = fs.create_finding(
        review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
        record=FindingRecord(observation="Generalized rhythmic delta activity", category="GRDA"),
        evidence_specs=[evidence_spec("inference", study.inference_id, "output-contract@1.0.0",
                                      confidence=0.9, source_lineage_id=study.inference_lineage_id)],
        review_lineage_id=review.lineage_id, inference_lineage_id=study.inference_lineage_id)
    fs.to_draft(finding); fs.submit_for_review(finding); fs.confirm(finding)
    finding, interp = fs.add_interpretation(
        finding, text="GRDA pattern; descriptive, non-diagnostic.",
        supporting_evidence=(finding.evidence_ids[0],), confidence_level="moderate",
        review_references=(review.review_id,))

    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    cid = ks.concept_by_name("Rhythmic Delta Activity")
    rel = ks.link_finding_to_concept(finding_id=finding.finding_id, concept_id=cid,
                                     finding_lineage_id=finding.lineage_id)
    ks.link_interpretation_to_concept(interpretation_id=interp.interpretation_id, concept_id=cid,
                                      interpretation_lineage_id=interp.lineage_id)
    ks.ground_concept_in_evidence(concept_id=cid, evidence_ref=finding.evidence_ids[0],
                                  evidence_kind="inference", evidence_lineage_id=finding.evidence[0].lineage_id)
    return {"tracker": tracker, "cs": cs, "rs": rs, "fs": fs, "ks": ks,
            "case": case, "review": review, "finding": finding, "interp": interp,
            "concept_id": cid, "rel": rel}


@pytest.fixture(scope="module")
def workflow(offline_run):
    _, run_dir = offline_run
    return _build(run_dir)


def test_full_chain_executes(workflow):
    assert workflow["finding"].status.value == "confirmed"
    assert workflow["interp"].interpretation_id in workflow["fs"].interpretation_store()
    assert workflow["concept_id"] is not None


def test_complete_traceability_spans_all_layers(workflow):
    """The finding→concept relationship node's chain spans the clinical + knowledge graphs."""
    tracker, rel = workflow["tracker"], workflow["rel"]
    chain = tracker.chain(rel.lineage_id)
    kinds = {r.kind for r in chain}
    assert {"patient", "case", "study", "review", "review_session", "inference",
            "evidence", "finding", "interpretation", "concept", "term", "relation"}.issubset(kinds)
    assert tracker.verify_chain(rel.lineage_id)


def test_all_validations_pass(workflow):
    assert workflow["cs"].validate(workflow["case"]).ok
    assert workflow["rs"].validate(workflow["review"]).ok
    assert workflow["fs"].validate(workflow["finding"]).ok
    assert workflow["ks"].validate().ok


def test_audit_trails_intact(workflow):
    fs, ks, finding = workflow["fs"], workflow["ks"], workflow["finding"]
    flog = fs.audit_log_for(finding.finding_id)
    assert flog.verify() and flog.head == finding.audit_head
    assert ks.audit.verify()


def test_v1_and_v2_lineage_remain_intact(offline_run, workflow):
    run, _ = offline_run
    # V1 inference run still validates, and its lineage node is reachable from the finding
    assert run.validation["ok"] is True
    tracker, finding = workflow["tracker"], workflow["finding"]
    assert any(r.lineage_id == run.lineage_id for r in tracker.chain(finding.lineage_id))
    # V2-P1/P2 case + review chains still verify
    assert workflow["cs"].lineage.verify_chain(workflow["case"].lineage_id)
    assert workflow["rs"].lineage.verify_chain(workflow["review"].lineage_id)


def test_workflow_is_reproducible(tmp_path):
    cfg = PipelineConfig(synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
                         training=TrainingConfig(steps=60), model_name="tcn")
    InferenceOrchestrator(cfg, output_dir=str(tmp_path / "a"), clock=FakeClock()).run()
    InferenceOrchestrator(cfg, output_dir=str(tmp_path / "b"), clock=FakeClock()).run()
    w1 = _build(str(tmp_path / "a"))
    w2 = _build(str(tmp_path / "b"))
    assert w1["finding"].finding_id == w2["finding"].finding_id
    assert w1["finding"].version.version == w2["finding"].version.version
    assert w1["ks"].version == w2["ks"].version
    assert w1["rel"].relation_id == w2["rel"].relation_id
