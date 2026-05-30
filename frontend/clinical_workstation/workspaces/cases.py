"""Case workspace — render registered case artifacts as Page view-models."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, metric_row, validation_badges
from ..visualizations import case_lifecycle


def case_pages(state) -> list:
    """One overview page + one page per case (metadata/state/audit/lineage/...)."""
    pages = [_overview(state)]
    for case in state.cases:
        pages.append(_case_detail(state, case))
    return pages


def _overview(state) -> Page:
    rows = []
    for c in state.cases:
        rec = c.get("registry_record", {})
        rows.append([c.get("case_id", "")[:18], c.get("patient_id", "")[:18],
                     rec.get("status"), rec.get("review_state"),
                     len(c.get("studies", [])), c.get("validation", {}).get("ok"),
                     c.get("lineage_verified")])
    sections = [
        kv_panel("Case Registry", {
            "n_cases": len(state.cases),
            "registry_version": state.registries.get("case_registry", {}).get("case_registry_version"),
            "patients": state.meta.get("patients"),
        }),
        table("Cases", ["case", "patient", "status", "review_state", "studies", "valid", "lineage_ok"], rows),
    ]
    return Page("cases-overview", "Cases — Overview", sections, [case_lifecycle(state.cases)])


def _case_detail(state, case: dict) -> Page:
    rec = case.get("registry_record", {})
    reports = case.get("reports", {})
    audit = case.get("audit", {})
    case_id = case.get("case_id", "")
    related_reviews = state.reviews_for_case(case_id)
    related_findings = state.findings_for_case(case_id)
    sections = [
        kv_panel("Case Metadata", {
            "case_id": case_id, "patient_id": case.get("patient_id"),
            "owner": rec.get("owner"), "creation_date": rec.get("creation_date"),
            "version": rec.get("version"), "registry_version": rec.get("case_registry_version"),
        }),
        badges("Case State", [
            ("status", rec.get("status", "?")),
            ("review_state", rec.get("review_state", "?")),
            ("audit_verified", audit.get("verified", False)),
            ("lineage_verified", case.get("lineage_verified", False)),
        ]),
        validation_badges("Case Validation", case.get("validation", {})),
        kv_panel("Case Lineage", {
            "lineage_id": case.get("lineage_id"),
            "lineage_report": reports.get("case_lineage_report", {}).get("n_nodes")
            or reports.get("case_lineage_report", {}).get("chain_length"),
        }),
        table("Case Dependencies & Relationships", ["relationship", "id"],
              [["study", s] for s in case.get("studies", [])]
              + [["review", r.get("review_id")] for r in related_reviews]
              + [["finding", f.get("finding_id")] for f in related_findings]),
        table("Case History (audit events)", ["seq", "event", "hash"],
              [[e.get("seq"), e.get("kind"), e.get("event_hash", "")[:8]]
               for e in audit.get("events", [])]),
        metric_row("Case Reports", {k: "available" for k in reports}),
    ]
    return Page(f"case-{case_id}", f"Case {case_id[:14]}", sections, [])
