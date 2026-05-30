"""Run the V2-P3 + V2-P4 clinical findings/knowledge workflow end to end.

Drives the full required deliverable with complete traceability:

    Patient → Case → Study → Review → Evidence → Finding → Interpretation →
    Knowledge Context → Audit Trail → Lineage Trail

It produces a real V1 inference run, builds a Case + Review (V2-P1/P2), records an
evidence-grounded Finding + a separate Interpretation (V2-P3), seeds the clinical
Knowledge base and links the Finding/Interpretation to a Concept (V2-P4), then
prints the audit + lineage trails. All subsystems share one lineage tracker.

    python -m scripts.run_clinical_knowledge_workflow
"""

from __future__ import annotations

import argparse
import tempfile

from datasets import SyntheticConfig
from ml.training import TrainingConfig
from backend.offline_inference import InferenceOrchestrator, PipelineConfig
from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService


def run(argv=None) -> dict:
    p = argparse.ArgumentParser(description="Run the NeuroVision AI V2-P3/P4 workflow end to end.")
    p.add_argument("--steps", type=int, default=80)
    p.add_argument("--reviewer", default="dr.reviewer")
    args = p.parse_args(argv)

    run_dir = tempfile.mkdtemp() + "/inference_run"
    inference = InferenceOrchestrator(
        PipelineConfig(synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
                       training=TrainingConfig(steps=args.steps), model_name="tcn"),
        output_dir=run_dir).run()
    print("=== V1 Offline Inference ===")
    print(f"inference_id : {inference.inference_id}  (validation ok: {inference.validation['ok']})")

    cs = CaseService()
    case = cs.create_case(patient_key="PT-DEID-K", case_key="ENC-K", owner="clinical-ops")
    cs.transition(case, CaseStatus.INGESTED, "ingested")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "processed")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready")
    study = case.studies[0]
    tracker = cs.lineage

    rs = ReviewService(lineage_tracker=tracker)
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()))
    rs.assign(review, assignee=args.reviewer, priority="urgent")
    cs.transition(case, CaseStatus.UNDER_REVIEW, "review started")
    review, sess = rs.start_session(review)

    fs = FindingService(lineage_tracker=tracker)
    finding = fs.create_finding(
        review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
        record=FindingRecord(observation="Generalized rhythmic delta activity", category="GRDA",
                             region="generalized"),
        evidence_specs=[evidence_spec("inference", study.inference_id, "output-contract@1.0.0",
                                      confidence=0.9, source_lineage_id=study.inference_lineage_id)],
        review_lineage_id=review.lineage_id, inference_lineage_id=study.inference_lineage_id,
        owner=args.reviewer)
    fs.to_draft(finding); fs.submit_for_review(finding); fs.confirm(finding)
    finding, interp = fs.add_interpretation(
        finding, text="Pattern consistent with GRDA. Descriptive only; not a diagnosis.",
        supporting_evidence=(finding.evidence_ids[0],), confidence_level="moderate",
        review_references=(review.review_id,))
    print("\n=== V2-P3 Findings & Interpretation ===")
    print(f"finding_id   : {finding.finding_id}  status={finding.status.value}  evidence={len(finding.evidence)}")
    print(f"interpretation: {interp.interpretation_id}  (separate entity; status={interp.interpretation_status})")

    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    cid = ks.concept_by_name("Rhythmic Delta Activity")
    rel = ks.link_finding_to_concept(finding_id=finding.finding_id, concept_id=cid,
                                     finding_lineage_id=finding.lineage_id)
    ks.link_interpretation_to_concept(interpretation_id=interp.interpretation_id, concept_id=cid,
                                      interpretation_lineage_id=interp.lineage_id)
    ks.ground_concept_in_evidence(concept_id=cid, evidence_ref=finding.evidence_ids[0],
                                  evidence_kind="inference", evidence_lineage_id=finding.evidence[0].lineage_id)
    print("\n=== V2-P4 Clinical Knowledge ===")
    print(f"knowledge ver: {ks.version[:24]}  terms={len(ks.terminology.list_terms())} "
          f"concepts={len(ks.concepts.list_concepts())} relationships={len(ks.relationships.list_relations())}")
    print(f"linked concept: {cid} ('Rhythmic Delta Activity')")

    chain = tracker.chain(rel.lineage_id)
    kinds = sorted(set(r.kind for r in chain))
    print("\n=== Trails ===")
    print(f"case valid   : {'OK' if cs.validate(case).ok else 'FAILED'} (7 checks)")
    print(f"review valid : {'OK' if rs.validate(review).ok else 'FAILED'} (7 checks)")
    print(f"finding valid: {'OK' if fs.validate(finding).ok else 'FAILED'} (7 checks)")
    print(f"knowledge val: {'OK' if ks.validate().ok else 'FAILED'} (7 checks)")
    print(f"lineage chain: verified={tracker.verify_chain(rel.lineage_id)} nodes={len(chain)}")
    print(f"chain kinds  : {kinds}")
    print(f"traceability : Patient -> Case -> Study -> Review -> Evidence -> Finding -> "
          f"Interpretation -> Knowledge ({'COMPLETE' if tracker.verify_chain(rel.lineage_id) else 'BROKEN'})")

    return {"inference_id": inference.inference_id, "case_id": case.case_id,
            "review_id": review.review_id, "finding_id": finding.finding_id,
            "interpretation_id": interp.interpretation_id, "concept_id": cid,
            "chain_verified": tracker.verify_chain(rel.lineage_id)}


if __name__ == "__main__":
    run()
