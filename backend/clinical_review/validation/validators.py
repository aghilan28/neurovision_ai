"""Review validation checks (V2-P2)."""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from backend.clinical_cases.identity import validate_identity  # intra-backend reuse

from ..models.domain import ReviewStatus


class ReviewValidationError(RuntimeError):
    """Raised when a mandated review-validation check fails."""


class ReviewValidator:
    def validate(self, *, review: Any, registry: Any, audit_log: Any, lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()

        # 1. session integrity
        sess_ok = True
        detail = "ok"
        for s in review.sessions:
            if s.review_id != review.review_id:
                sess_ok, detail = False, f"session {s.session_id} not linked to review"
                break
            if (not s.is_open) and (s.session_end is None):
                sess_ok, detail = False, f"closed session {s.session_id} missing end"
                break
            viewed = set(s.artifacts_viewed)
            if review.artifact_refs and not viewed.issubset(set(review.artifact_refs)):
                sess_ok, detail = False, f"session {s.session_id} viewed unregistered artifacts"
                break
        report.add("session_integrity", bool(sess_ok), detail)

        # 2. registry integrity
        try:
            rec = registry.get(review.review_id)
            reg_ok = (rec.case_id == review.case_id and rec.version == review.version.version
                      and rec.lineage_id == review.lineage_id
                      and set(rec.assignment_ids) == set(review.assignment_ids))
            report.add("registry_integrity", bool(reg_ok),
                       f"registered version={rec.version} review version={review.version.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. audit integrity
        try:
            verify_ok = audit_log.verify()
            head_ok = review.audit_head == audit_log.head
            report.add("audit_integrity", bool(verify_ok and head_ok),
                       f"chain_verified={verify_ok} head_match={head_ok}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 4. lineage integrity
        try:
            chain_ok = bool(review.lineage_id) and lineage_tracker.verify_chain(review.lineage_id)
            case_linked = (review.case_lineage_id is None) or lineage_tracker.exists(review.case_lineage_id)
            inf_linked = (review.inference_lineage_id is None) or lineage_tracker.exists(review.inference_lineage_id)
            report.add("lineage_integrity", bool(chain_ok and case_linked and inf_linked),
                       f"chain_ok={chain_ok} case_linked={case_linked} inference_linked={inf_linked}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 5. assignment integrity
        try:
            active = [a for a in review.assignments if a.status == "active"]
            assignees_ok = all(a.assignee for a in review.assignments)
            one_active = len(active) <= 1
            reviewer_ok = True
            if review.status not in (ReviewStatus.CREATED,) and active:
                reviewer_ok = review.reviewer == active[0].assignee
            report.add("assignment_integrity", bool(assignees_ok and one_active and reviewer_ok),
                       f"n_assignments={len(review.assignments)} active={len(active)}")
        except Exception as exc:
            report.add("assignment_integrity", False, f"error: {exc}")

        # 6. status integrity
        try:
            status_ok = isinstance(review.status, ReviewStatus)
            n_status_changes = sum(1 for e in audit_log.events() if e.kind == "status_change")
            count_ok = review.transition_count == n_status_changes
            id_ok = validate_identity(review.review_id, "review")[0]
            report.add("status_integrity", bool(status_ok and count_ok and id_ok),
                       f"status={review.status.value} transitions={review.transition_count} "
                       f"audited={n_status_changes}")
        except Exception as exc:
            report.add("status_integrity", False, f"error: {exc}")

        # 7. version integrity
        try:
            from ..models.domain import ReviewVersion
            expected = ReviewVersion.compute(review.state_signature(), review.version.previous)
            ver_ok = review.version.version == expected
            report.add("version_integrity", bool(ver_ok),
                       f"recorded={review.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise ReviewValidationError(f"review validation failed: {names}")
