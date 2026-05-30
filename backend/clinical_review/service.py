"""ReviewService — the governed orchestration hub for the Clinical Review Workflow.

Ties identity, workflow (lifecycle), sessions, assignment, tracking, registry,
audit, and lineage into the use cases that create and evolve a Review, run review
sessions over a Case's registered V1 artifacts, and assign/track reviewers.

Every mutation is: validated → audited (immutable) → lineage-extended →
version-bumped → registry-synced. Reviews link to a Case (V2-P1) and to the V1
inference they review (integration with V1 lineage/artifact systems).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ml.lineage import LineageTracker, make_lineage_record  # allowed: backend -> ml

from backend.clinical_cases.identity import mint_identity  # intra-backend reuse

from .version import CLINICAL_REVIEW_VERSION, REVIEW_REGISTRY_VERSION, DETERMINISTIC_EPOCH
from .models.domain import (
    ReviewStatus, ReviewIdentity, ReviewVersion, ReviewRegistryRecord, Review,
)
from .workflow import ReviewLifecycle
from .sessions import SessionManager
from .assignment import AssignmentManager
from .tracking import ReviewTracker
from .audit import make_review_audit_log
from .lineage import make_review_lineage, make_session_lineage, review_version_bundle
from .registry import ReviewRegistry
from .validation import ReviewValidator
from .reports import (
    build_review_summary_report, build_review_audit_report, build_review_lineage_report,
    build_review_assignment_report, build_review_validation_report, build_review_progress_report,
)


class ReviewService:
    """Stateful service holding the registry, a shared lineage tracker, per-review audit logs."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[ReviewRegistry] = None):
        self.registry = registry or ReviewRegistry()
        self.lineage = lineage_tracker or LineageTracker()
        self.lifecycle = ReviewLifecycle()
        self.sessions = SessionManager()
        self.assignments = AssignmentManager()
        self.tracker = ReviewTracker()
        self.validator = ReviewValidator()
        self._audit_logs: dict[str, object] = {}

    def audit_log_for(self, review_id: str):
        return self._audit_logs[review_id]

    # --- create ---------------------------------------------------------------
    def create_review(self, *, case_id: str, case_lineage_id: Optional[str] = None,
                      study_id: Optional[str] = None, inference_lineage_id: Optional[str] = None,
                      artifact_refs: tuple = (), review_key: Optional[str] = None,
                      owner: str = "clinical-ops", created_at: str = DETERMINISTIC_EPOCH) -> Review:
        review_key = review_key or (study_id or "primary")
        rid = mint_identity("review", {"case_id": case_id, "review_key": review_key})

        node = self.lineage.record(make_review_lineage(
            rid.id, case_id, case_lineage_id=case_lineage_id or "",
            inference_lineage_id=inference_lineage_id, created_at=created_at)) \
            if case_lineage_id else self.lineage.record(make_lineage_record(
                kind="review", versions=review_version_bundle(),
                inputs={"case_id": case_id, "review_id": rid.id}, outputs={"review_id": rid.id},
                parents=(), created_at=created_at))

        log = make_review_audit_log()
        self._audit_logs[rid.id] = log
        log.append("review_created", {"review_id": rid.id, "case_id": case_id,
                                      "review_lineage_id": node.lineage_id}, created_at=created_at)

        review = Review(
            identity=ReviewIdentity(rid.id, case_id, rid.identity_version),
            case_id=case_id, study_id=study_id, status=ReviewStatus.CREATED,
            version=ReviewVersion(version="", previous=None, reason="created", created_at=created_at),
            owner=owner, created_at=created_at, artifact_refs=tuple(artifact_refs),
            lineage_id=node.lineage_id, audit_head=log.head,
            case_lineage_id=case_lineage_id, inference_lineage_id=inference_lineage_id)
        review.history = review.history.appended({"event": "created", "status": review.status.value})
        self._finalize(review, reason="created", created_at=created_at)
        return review

    # --- assignment -----------------------------------------------------------
    def assign(self, review: Review, *, assignee: str, priority: str = "routine", reason: str = "",
               created_at: str = DETERMINISTIC_EPOCH) -> Review:
        assignment = self.assignments.new_assignment(
            review_id=review.review_id, case_id=review.case_id, assignee=assignee,
            index=len(review.assignments), priority=priority, reason=reason, date=created_at)
        review.assignments = review.assignments + (assignment,)
        review.reviewer = assignee
        log = self._audit_logs[review.review_id]
        log.append("assignment_created", assignment.to_dict(), created_at=created_at)
        if review.status == ReviewStatus.CREATED:
            self._do_transition(review, ReviewStatus.ASSIGNED, reason=f"assigned:{assignee}",
                                created_at=created_at)
        self._finalize(review, reason=f"assign:{assignee}", created_at=created_at)
        return review

    def reassign(self, review: Review, *, new_assignee: str, reason: str = "",
                 created_at: str = DETERMINISTIC_EPOCH) -> Review:
        active = [a for a in review.assignments if a.status == "active"]
        if not active:
            raise ValueError("no active assignment to reassign")
        closed, fresh = self.assignments.reassign(active[-1], new_assignee=new_assignee,
                                                  index=len(review.assignments), reason=reason, date=created_at)
        others = tuple(a for a in review.assignments if a.assignment_id != closed.assignment_id)
        review.assignments = others + (closed, fresh)
        review.reviewer = new_assignee
        log = self._audit_logs[review.review_id]
        log.append("reassigned", {"from": closed.assignee, "to": new_assignee, "reason": reason},
                   created_at=created_at)
        self._finalize(review, reason=f"reassign:{new_assignee}", created_at=created_at)
        return review

    # --- sessions -------------------------------------------------------------
    def start_session(self, review: Review, *, reviewer: Optional[str] = None,
                      created_at: str = DETERMINISTIC_EPOCH):
        reviewer = reviewer or review.reviewer
        if not reviewer:
            raise ValueError("cannot start a session without an assigned reviewer")
        session = self.sessions.new_session(
            review_id=review.review_id, reviewer=reviewer, case_id=review.case_id,
            study_id=review.study_id, index=len(review.sessions), start=created_at)
        session_node = self.lineage.record(make_session_lineage(
            session.session_id, review.review_id, review_lineage_id=review.lineage_id,
            study_id=review.study_id, created_at=created_at))
        log = self._audit_logs[review.review_id]
        log.append("session_started", {"session_id": session.session_id, "reviewer": reviewer},
                   created_at=created_at)
        review.sessions = review.sessions + (session,)
        if review.status == ReviewStatus.ASSIGNED:
            self._do_transition(review, ReviewStatus.IN_PROGRESS, reason="session_started",
                                created_at=created_at, parents_extra=(session_node.lineage_id,))
        else:
            self._advance_review(review, parents_extra=(session_node.lineage_id,),
                                 reason="session_started", created_at=created_at)
        self._finalize(review, reason=f"session_start:{session.session_id}", created_at=created_at)
        return review, session

    def record_session_activity(self, review: Review, session, *, artifacts_viewed=(),
                                reports_viewed=(), actions=(), notes: str = "",
                                created_at: str = DETERMINISTIC_EPOCH):
        s = session
        if artifacts_viewed:
            s = self.sessions.view_artifacts(s, artifacts_viewed)
        if reports_viewed:
            s = self.sessions.view_reports(s, reports_viewed)
        for a in actions:
            s = self.sessions.record_action(s, a)
        if notes:
            s = replace(s, review_notes=notes)
        log = self._audit_logs[review.review_id]
        log.append("artifact_access", {"session_id": s.session_id,
                                        "artifacts_viewed": list(artifacts_viewed),
                                        "reports_viewed": list(reports_viewed)}, created_at=created_at)
        if actions:
            log.append("review_action", {"session_id": s.session_id, "actions": list(actions)},
                       created_at=created_at)
        review.sessions = self._replace_session(review.sessions, s)
        self._finalize(review, reason=f"session_activity:{s.session_id}", created_at=created_at)
        return review, s

    def end_session(self, review: Review, session, *, outcome: str, notes: str = "",
                    created_at: str = DETERMINISTIC_EPOCH):
        s = self.sessions.close(session, outcome=outcome, notes=notes, end=created_at)
        log = self._audit_logs[review.review_id]
        log.append("session_ended", {"session_id": s.session_id, "outcome": outcome},
                   created_at=created_at)
        review.sessions = self._replace_session(review.sessions, s)
        self._finalize(review, reason=f"session_end:{s.session_id}", created_at=created_at)
        return review, s

    # --- lifecycle convenience ------------------------------------------------
    def submit_for_confirmation(self, review, created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.PENDING_CONFIRMATION, "submit", created_at)

    def complete(self, review, created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.COMPLETED, "complete", created_at)

    def reopen(self, review, reason="reopen", created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.REOPENED, reason, created_at)

    def resume(self, review, created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.IN_PROGRESS, "resume", created_at)

    def close(self, review, created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.CLOSED, "close", created_at)

    def archive(self, review, created_at=DETERMINISTIC_EPOCH):
        return self.transition(review, ReviewStatus.ARCHIVED, "archive", created_at)

    def transition(self, review: Review, target: ReviewStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> Review:
        self._do_transition(review, target, reason=reason, created_at=created_at)
        self._finalize(review, reason=f"transition:{target.value}", created_at=created_at)
        return review

    # --- validation + reports -------------------------------------------------
    def validate(self, review: Review):
        return self.validator.validate(review=review, registry=self.registry,
                                       audit_log=self._audit_logs[review.review_id],
                                       lineage_tracker=self.lineage)

    def reports(self, review: Review) -> dict:
        log = self._audit_logs[review.review_id]
        validation = self.validate(review).to_dict()
        return {
            "review_summary_report": build_review_summary_report(review),
            "review_audit_report": build_review_audit_report(review, log),
            "review_lineage_report": build_review_lineage_report(review, self.lineage),
            "review_assignment_report": build_review_assignment_report(review),
            "review_validation_report": build_review_validation_report(review, validation),
            "review_progress_report": build_review_progress_report(review, log),
        }

    def tracking(self, review: Review) -> dict:
        return self.tracker.summarize(review, self._audit_logs[review.review_id])

    # --- internals ------------------------------------------------------------
    def _do_transition(self, review: Review, target: ReviewStatus, *, reason: str,
                       created_at: str, parents_extra: tuple = ()) -> None:
        record = self.lifecycle.transition(review.status, target, reason=reason, created_at=created_at)
        log = self._audit_logs[review.review_id]
        log.append("status_change", record.to_dict(), created_at=created_at)
        review.status = target
        review.transition_count += 1
        review.history = review.history.appended({"event": "status_change", "to": target.value,
                                                  "reason": reason})
        self._advance_review(review, parents_extra=parents_extra, reason=f"transition:{target.value}",
                             created_at=created_at, extra_outputs={"transition": record.to_dict()})

    def _advance_review(self, review: Review, *, parents_extra: tuple = (), reason: str,
                        created_at: str, extra_outputs: Optional[dict] = None) -> None:
        outputs = {"review_id": review.review_id, "status": review.status.value}
        if extra_outputs:
            outputs.update(extra_outputs)
        node = self.lineage.record(make_lineage_record(
            kind="review", versions=review_version_bundle(),
            inputs={"review_id": review.review_id, "case_id": review.case_id},
            outputs=outputs, parents=(review.lineage_id,) + tuple(parents_extra), created_at=created_at))
        review.lineage_id = node.lineage_id

    def _finalize(self, review: Review, *, reason: str, created_at: str) -> None:
        previous = review.version.version or None
        review.version = ReviewVersion(version=ReviewVersion.compute(review.state_signature(), previous),
                                       previous=previous, reason=reason, created_at=created_at)
        log = self._audit_logs[review.review_id]
        log.append("version_changed", {"version": review.version.version, "reason": reason},
                   created_at=created_at)
        review.audit_head = log.head
        self._sync_registry(review)

    def _sync_registry(self, review: Review) -> None:
        self.registry.register(ReviewRegistryRecord(
            review_id=review.review_id, case_id=review.case_id, reviewer=review.reviewer,
            version=review.version.version, status=review.status,
            assignment_ids=review.assignment_ids, artifact_refs=review.artifact_refs,
            audit_state=review.audit_head, lineage_id=review.lineage_id,
            review_registry_version=REVIEW_REGISTRY_VERSION))

    @staticmethod
    def _replace_session(sessions: tuple, updated) -> tuple:
        return tuple(updated if s.session_id == updated.session_id else s for s in sessions)
