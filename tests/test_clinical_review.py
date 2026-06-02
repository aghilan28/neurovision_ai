"""Tests for the Clinical Review Workflow (V2-P2).

Covers review lifecycle, sessions, assignment, tracking, registry, immutable audit,
lineage, validation, reports, recovery, and deterministic reproducibility.
"""

from __future__ import annotations

import pytest

from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import (
    ReviewService, ReviewStatus, ReviewRegistry, ReviewLifecycle, ReviewLifecycleError,
    AssignmentManager, AssignmentError, ReviewTracker, make_review_audit_log,
)


@pytest.fixture
def linked(offline_run):
    """A case (READY_FOR_REVIEW) with an attached V1 study, sharing a lineage tracker."""
    _, run_dir = offline_run
    cs = CaseService()
    case = cs.create_case(patient_key="PT-R", case_key="ENC-R", owner="dr.kiro")
    cs.transition(case, CaseStatus.INGESTED, "ingest")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "proc")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready")
    rs = ReviewService(lineage_tracker=cs.lineage)  # SHARE the tracker
    study = case.studies[0]
    return cs, rs, case, study


@pytest.fixture
def review(linked):
    cs, rs, case, study = linked
    return rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                            study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                            artifact_refs=tuple(study.artifact_refs.keys()), owner="dr.kiro")


# --- workflow lifecycle -------------------------------------------------------
def test_review_lifecycle_full_path(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev", priority="urgent")
    assert review.status == ReviewStatus.ASSIGNED and review.reviewer == "dr.rev"
    review, sess = rs.start_session(review)
    assert review.status == ReviewStatus.IN_PROGRESS
    rs.submit_for_confirmation(review)
    assert review.status == ReviewStatus.PENDING_CONFIRMATION
    rs.complete(review)
    assert review.status == ReviewStatus.COMPLETED
    rs.close(review)
    assert review.status == ReviewStatus.CLOSED
    assert rs.validate(review).ok


def test_forbidden_review_transition_blocked():
    lc = ReviewLifecycle()
    with pytest.raises(ReviewLifecycleError):
        lc.transition(ReviewStatus.CREATED, ReviewStatus.COMPLETED)
    assert lc.is_terminal(ReviewStatus.ARCHIVED)


def test_reopen_path(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev")
    review, sess = rs.start_session(review)
    rs.submit_for_confirmation(review)
    rs.complete(review)
    rs.reopen(review, reason="addendum")
    assert review.status == ReviewStatus.REOPENED
    rs.resume(review)
    assert review.status == ReviewStatus.IN_PROGRESS
    tracking = rs.tracking(review)
    assert tracking["reopen_events"] == 1 and tracking["revisions"] == 1


# --- sessions -----------------------------------------------------------------
def test_session_records_artifacts_and_outcome(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev")
    review, sess = rs.start_session(review)
    refs = list(study.artifact_refs.keys())[:3]
    review, sess = rs.record_session_activity(review, sess, artifacts_viewed=refs,
                                              reports_viewed=["summary_report"],
                                              actions=["viewed_calibration"], notes="ok")
    review, sess = rs.end_session(review, sess, outcome="confirmed", notes="done")
    assert not sess.is_open and sess.review_outcome == "confirmed"
    assert set(sess.artifacts_viewed) == set(refs)
    assert "viewed_calibration" in sess.actions_taken
    assert rs.validate(review).ok


def test_session_viewing_unregistered_artifact_fails_validation(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev")
    review, sess = rs.start_session(review)
    review, sess = rs.record_session_activity(review, sess, artifacts_viewed=["NOT-A-REAL-ARTIFACT"])
    rep = rs.validate(review)
    assert not rep.ok
    assert any(c.name == "session_integrity" and not c.passed for c in rep.checks)


# --- assignment ---------------------------------------------------------------
def test_assignment_and_reassignment(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.a", priority="routine")
    rs.reassign(review, new_assignee="dr.b", reason="load balancing")
    assert review.reviewer == "dr.b"
    active = [a for a in review.assignments if a.status == "active"]
    reassigned = [a for a in review.assignments if a.status == "reassigned"]
    assert len(active) == 1 and active[0].assignee == "dr.b"
    assert len(reassigned) == 1 and reassigned[0].assignee == "dr.a"
    assert rs.validate(review).ok


def test_assignment_priority_validation():
    with pytest.raises(AssignmentError):
        AssignmentManager.new_assignment(review_id="review+0000000000000000", case_id="case+0000000000000000",
                                         assignee="x", index=0, priority="bogus")


def test_escalation_hook_is_inert_but_tracked():
    a = AssignmentManager.new_assignment(review_id="review+0000000000000000",
                                         case_id="case+0000000000000000", assignee="x", index=0)
    e = AssignmentManager.escalate(a)
    assert e.escalation_level == 1 and a.escalation_level == 0  # immutable; no side effects


# --- registry + audit ---------------------------------------------------------
def test_review_registry_rejects_silent_overwrite(linked, review):
    cs, rs, case, study = linked
    rec = rs.registry.get(review.review_id)
    from backend.clinical_review.models import ReviewRegistryRecord
    tampered = ReviewRegistryRecord(
        review_id=rec.review_id, case_id="case+ffffffffffffffff", reviewer=rec.reviewer,
        version=rec.version, status=rec.status, assignment_ids=rec.assignment_ids,
        artifact_refs=rec.artifact_refs, audit_state=rec.audit_state, lineage_id=rec.lineage_id)
    with pytest.raises(ValueError):
        rs.registry.register(tampered)


def test_review_audit_is_tamper_evident(linked, review):
    cs, rs, case, study = linked
    log = rs.audit_log_for(review.review_id)
    assert log.verify() and log.head == review.audit_head
    object.__setattr__(log.events()[1], "payload", {"tampered": True})
    assert log.verify() is False


# --- lineage + reports + tracking ---------------------------------------------
def test_review_lineage_chains_to_case_and_inference(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev")
    review, sess = rs.start_session(review)
    assert rs.lineage.verify_chain(review.lineage_id)
    kinds = {r.kind for r in rs.lineage.chain(review.lineage_id)}
    assert {"review", "review_session", "case", "study", "inference"}.issubset(kinds)


def test_review_reports_generate(linked, review):
    cs, rs, case, study = linked
    rs.assign(review, assignee="dr.rev")
    reps = rs.reports(review)
    assert set(reps) == {"review_summary_report", "review_audit_report", "review_lineage_report",
                         "review_assignment_report", "review_validation_report", "review_progress_report"}
    assert reps["review_validation_report"]["validation"]["ok"]


def test_review_creation_is_deterministic(linked):
    cs, rs, case, study = linked
    r1 = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id, study_id=study.study_id)
    rs2 = ReviewService(lineage_tracker=cs.lineage)
    r2 = rs2.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id, study_id=study.study_id)
    assert r1.review_id == r2.review_id
