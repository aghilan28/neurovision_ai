"""Shared builders for the V2-P5 / V2-P6 test suites.

Builds a small, deterministic multi-case population through the *real* V2 services
(sharing one lineage tracker), so the intelligence/decision layers are exercised
against genuine Case/Review/Finding/Interpretation/Knowledge aggregates — no
synthetic stand-ins. Not collected by pytest (no ``test_`` prefix).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.clinical_cases import CaseService
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService
from backend.multi_case_intelligence import PopulationBuilder, PopulationView


@dataclass
class MultiCase:
    cs: CaseService
    rs: ReviewService
    fs: FindingService
    ks: KnowledgeService
    population: PopulationView
    cases: dict
    findings: dict


def _new_review(rs, case, *, finalize: bool):
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id, study_id=None,
                              inference_lineage_id=None, artifact_refs=())
    rs.assign(review, assignee="dr.rev")
    review, _ = rs.start_session(review)
    if finalize:
        rs.submit_for_confirmation(review)
        rs.complete(review)
    return review


def build_multicase() -> MultiCase:
    cs = CaseService()
    ks = KnowledgeService(lineage_tracker=cs.lineage).seed_default_knowledge()
    rs = ReviewService(lineage_tracker=cs.lineage)
    fs = FindingService(lineage_tracker=cs.lineage)
    pb = PopulationBuilder()

    cases: dict = {}
    findings: dict = {}

    # --- Case 1 (patient PT1): two findings, one finalized review, interpretation
    c1 = cs.create_case(patient_key="PT1", case_key="ENC1", owner="ops")
    r1 = _new_review(rs, c1, finalize=True)
    f1 = fs.create_finding(review_id=r1.review_id, case_id=c1.case_id, study_id=None,
            record=FindingRecord(observation="lateralized periodic discharges", category="LPD"),
            evidence_specs=[evidence_spec("inference", "inf-1", "output-contract@1.0.0", confidence=0.9),
                            evidence_spec("coverage", "cov-1", "coverage@1.0.0", confidence=0.92)],
            review_lineage_id=r1.lineage_id)
    f1, _ = fs.add_interpretation(f1, text="LPD pattern", confidence_level="high")
    f1 = fs.to_draft(f1); f1 = fs.submit_for_review(f1); f1 = fs.confirm(f1)
    f2 = fs.create_finding(review_id=r1.review_id, case_id=c1.case_id, study_id=None,
            record=FindingRecord(observation="generalized periodic discharges", category="GPD"),
            evidence_specs=[evidence_spec("inference", "inf-2", "output-contract@1.0.0", confidence=0.55)],
            review_lineage_id=r1.lineage_id)
    cases["C1"] = c1
    findings["F1"], findings["F2"] = f1, f2
    pb.add_case(c1).add_review(r1).add_finding(f1).add_finding(f2)
    for i in fs.interpretation_store().values():
        pb.add_interpretation(i)

    # --- Case 2 (patient PT2): low-confidence finding, in-progress review
    c2 = cs.create_case(patient_key="PT2", case_key="ENC2", owner="ops")
    r2 = _new_review(rs, c2, finalize=False)
    f3 = fs.create_finding(review_id=r2.review_id, case_id=c2.case_id, study_id=None,
            record=FindingRecord(observation="rhythmic delta", category="GRDA"),
            evidence_specs=[evidence_spec("inference", "inf-3", "output-contract@1.0.0", confidence=0.3)],
            review_lineage_id=r2.lineage_id)
    cases["C2"] = c2
    findings["F3"] = f3
    pb.add_case(c2).add_review(r2).add_finding(f3)

    # --- Case 3 (patient PT3): finding in an unknown category (knowledge gap)
    c3 = cs.create_case(patient_key="PT3", case_key="ENC3", owner="ops")
    r3 = _new_review(rs, c3, finalize=False)
    f4 = fs.create_finding(review_id=r3.review_id, case_id=c3.case_id, study_id=None,
            record=FindingRecord(observation="unusual waveform", category="unknown_pattern"),
            evidence_specs=[evidence_spec("inference", "inf-4", "output-contract@1.0.0", confidence=0.8)],
            review_lineage_id=r3.lineage_id)
    cases["C3"] = c3
    findings["F4"] = f4
    pb.add_case(c3).add_review(r3).add_finding(f4)

    pb.add_knowledge_service(ks)
    return MultiCase(cs=cs, rs=rs, fs=fs, ks=ks, population=pb.build(), cases=cases, findings=findings)
