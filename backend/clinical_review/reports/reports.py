"""Review report builders (reproducible; version-tagged)."""

from __future__ import annotations

from typing import Any

from ..version import REVIEW_REPORT_VERSION, CLINICAL_REVIEW_VERSION
from ..workflow import REVIEW_TRANSITIONS, ReviewLifecycle
from ..tracking import ReviewTracker


def _header(report_type: str, review: Any) -> dict:
    return {
        "report_type": report_type,
        "review_report_version": REVIEW_REPORT_VERSION,
        "clinical_review_version": CLINICAL_REVIEW_VERSION,
        "review_id": review.review_id,
        "case_id": review.case_id,
        "review_version": review.version.version,
    }


def build_review_summary_report(review: Any) -> dict:
    return {
        **_header("review_summary", review),
        "status": review.status.value,
        "owner": review.owner,
        "reviewer": review.reviewer,
        "study_id": review.study_id,
        "n_sessions": len(review.sessions),
        "n_assignments": len(review.assignments),
        "artifact_refs": list(review.artifact_refs),
        "lineage_id": review.lineage_id,
        "audit_head": review.audit_head,
        "allowed_next": sorted(t.value for t in ReviewLifecycle.allowed_targets(review.status)),
    }


def build_review_audit_report(review: Any, audit_log: Any) -> dict:
    return {
        **_header("review_audit", review),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_review_lineage_report(review: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(review.lineage_id) if review.lineage_id else []
    return {
        **_header("review_lineage", review),
        "lineage_id": review.lineage_id,
        "case_lineage_id": review.case_lineage_id,
        "inference_lineage_id": review.inference_lineage_id,
        "chain_verified": lineage_tracker.verify_chain(review.lineage_id) if review.lineage_id else False,
        "chain_length": len(chain),
        "chain": [r.to_dict() for r in chain],
    }


def build_review_assignment_report(review: Any) -> dict:
    return {
        **_header("review_assignment", review),
        "current_reviewer": review.reviewer,
        "n_assignments": len(review.assignments),
        "assignments": [a.to_dict() for a in review.assignments],
    }


def build_review_validation_report(review: Any, validation_report_dict: dict) -> dict:
    return {**_header("review_validation", review), "validation": validation_report_dict}


def build_review_progress_report(review: Any, audit_log: Any) -> dict:
    return {**_header("review_progress", review),
            "tracking": ReviewTracker.summarize(review, audit_log),
            "state_machine": {s.value: sorted(t.value for t in targets)
                              for s, targets in REVIEW_TRANSITIONS.items()}}
