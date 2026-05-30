"""Shared builders for the V3-P1 / V3-P2 test suites.

Drives a small, deterministic multi-case workflow through the *real* V2 services
(sharing one lineage tracker), then observes their immutable audit logs with the
V3-P1 event adapters to produce events, and exposes both. Not collected by pytest
(no ``test_`` prefix).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService
from backend.operational_events import OperationalEventService
from backend.operational_events.generation import (
    CaseEventAdapter, ReviewEventAdapter, FindingEventAdapter, KnowledgeEventAdapter,
)

EPOCH = "1970-01-01T00:00:00Z"


@dataclass
class V3Fixture:
    cs: CaseService
    rs: ReviewService
    fs: FindingService
    ks: KnowledgeService
    events: OperationalEventService
    all_events: list
    cases: dict
    reviews: dict
    findings: dict


def _full_case(cs, rs, fs, patient, enc, category, conf):
    case = cs.create_case(patient_key=patient, case_key=enc, owner="ops")
    for st in (CaseStatus.INGESTED, CaseStatus.PROCESSING, CaseStatus.READY_FOR_REVIEW,
               CaseStatus.UNDER_REVIEW, CaseStatus.REVIEWED):
        cs.transition(case, st, "x")
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=None, inference_lineage_id=None, artifact_refs=())
    rs.assign(review, assignee="dr")
    review, sess = rs.start_session(review)
    review, sess = rs.end_session(review, sess, outcome="confirmed", notes="ok")
    rs.submit_for_confirmation(review)
    rs.complete(review)
    finding = fs.create_finding(
        review_id=review.review_id, case_id=case.case_id, study_id=None,
        record=FindingRecord(observation=category, category=category),
        evidence_specs=[evidence_spec("inference", f"inf-{enc}", "output-contract@1.0.0", confidence=conf),
                        evidence_spec("coverage", f"cov-{enc}", "coverage@1.0.0", confidence=min(0.99, conf + 0.03))],
        review_lineage_id=review.lineage_id)
    finding, _ = fs.add_interpretation(finding, text=f"{category} pattern", confidence_level="high")
    finding = fs.to_draft(finding)
    finding = fs.submit_for_review(finding)
    finding = fs.confirm(finding)
    return case, review, finding


def build_v3(n_cases: int = 2) -> V3Fixture:
    cs = CaseService()
    tracker = cs.lineage
    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    rs = ReviewService(lineage_tracker=tracker)
    fs = FindingService(lineage_tracker=tracker)

    plan = [("PT-001", "ENC-1", "LPD", 0.9), ("PT-002", "ENC-2", "GPD", 0.6),
            ("PT-003", "ENC-3", "SZ", 0.8)][:n_cases]
    cases, reviews, findings = {}, {}, {}
    for patient, enc, cat, conf in plan:
        c, r, f = _full_case(cs, rs, fs, patient, enc, cat, conf)
        cases[c.case_id] = c
        reviews[r.review_id] = r
        findings[f.finding_id] = f

    evs = OperationalEventService(lineage_tracker=tracker)
    all_events = []
    ordinal = 0
    for c in cases.values():
        all_events += CaseEventAdapter(evs).observe_log(
            source_entity_id=c.case_id, source_version=cs.registry.get(c.case_id).version,
            audit_log=cs.audit_log_for(c.case_id), source_lineage_id=c.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    for r in reviews.values():
        all_events += ReviewEventAdapter(evs).observe_log(
            source_entity_id=r.review_id, source_version=rs.registry.get(r.review_id).version,
            audit_log=rs.audit_log_for(r.review_id), source_lineage_id=r.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    for f in findings.values():
        all_events += FindingEventAdapter(evs).observe_log(
            source_entity_id=f.finding_id, source_version=fs.registry.get(f.finding_id).version,
            audit_log=fs.audit_log_for(f.finding_id), source_lineage_id=f.lineage_id,
            ingestion_ordinal=ordinal, created_at=EPOCH)
        ordinal += 1
    # knowledge events (single shared knowledge audit log; parented by the
    # knowledge lineage head so knowledge events are traceable too)
    all_events += KnowledgeEventAdapter(evs).observe_log(
        source_entity_id="knowledge", source_version=ks.registry.to_dict().get("knowledge_registry_version", "v1"),
        audit_log=ks.audit, source_lineage_id=ks.head_lineage_id,
        ingestion_ordinal=ordinal, created_at=EPOCH)

    return V3Fixture(cs=cs, rs=rs, fs=fs, ks=ks, events=evs, all_events=all_events,
                     cases=cases, reviews=reviews, findings=findings)
