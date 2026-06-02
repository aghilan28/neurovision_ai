"""Review workspace — render registered review artifacts as Page view-models."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, metric_row, validation_badges
from ..visualizations import review_lifecycle


def review_pages(state) -> list:
    pages = [_overview(state)]
    for review in state.reviews:
        pages.append(_review_detail(review))
    return pages


def _overview(state) -> Page:
    rows = []
    for r in state.reviews:
        rec = r.get("registry_record", {})
        trk = r.get("tracking", {})
        rows.append([r.get("review_id", "")[:18], r.get("case_id", "")[:14],
                     rec.get("status"), rec.get("reviewer"),
                     round(trk.get("progress", 0.0), 2), trk.get("n_sessions"),
                     r.get("validation", {}).get("ok")])
    sections = [
        kv_panel("Review Registry", {
            "n_reviews": len(state.reviews),
            "registry_version": state.registries.get("review_registry", {}).get("review_registry_version"),
        }),
        table("Reviews", ["review", "case", "status", "reviewer", "progress", "sessions", "valid"], rows),
    ]
    return Page("reviews-overview", "Reviews — Overview", sections, [review_lifecycle(state.reviews)])


def _review_detail(review: dict) -> Page:
    rec = review.get("registry_record", {})
    trk = review.get("tracking", {})
    audit = review.get("audit", {})
    reports = review.get("reports", {})
    rid = review.get("review_id", "")
    sections = [
        kv_panel("Review Status", {
            "review_id": rid, "case_id": review.get("case_id"),
            "status": rec.get("status"), "reviewer": rec.get("reviewer"),
            "version": rec.get("version"),
        }),
        metric_row("Progress", {
            "progress": trk.get("progress"), "milestones_reached": trk.get("milestones_reached"),
            "n_sessions": trk.get("n_sessions"), "n_completed_sessions": trk.get("n_completed_sessions"),
            "is_complete": trk.get("is_complete"),
        }),
        badges("Review Flags", [
            ("complete", trk.get("is_complete", False)),
            ("audit_verified", audit.get("verified", False)),
            ("lineage_verified", review.get("lineage_verified", False)),
        ]),
        table("Assignments",
              ["assignment", "assignee", "status"],
              [[a.get("assignment_id", "")[:18], a.get("assignee"), a.get("status")]
               for a in reports.get("review_assignment_report", {}).get("assignments", [])]),
        table("Review Sessions / History", ["seq", "event", "hash"],
              [[e.get("seq"), e.get("kind"), e.get("event_hash", "")[:8]]
               for e in audit.get("events", [])]),
        validation_badges("Validation Results", review.get("validation", {})),
        kv_panel("Lineage Information", {"lineage_id": review.get("lineage_id")}),
    ]
    return Page(f"review-{rid}", f"Review {rid[:14]}", sections, [])
