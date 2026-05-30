"""Reporting workspace — a report center indexing every registered report."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table


def _collect(state) -> list:
    """Collect (domain, owner_id, report_name) for every registered report."""
    rows = []
    for c in state.cases:
        for name in c.get("reports", {}):
            rows.append(["case", c.get("case_id", "")[:14], name])
    for r in state.reviews:
        for name in r.get("reports", {}):
            rows.append(["review", r.get("review_id", "")[:14], name])
    for f in state.findings:
        for name in f.get("reports", {}):
            rows.append(["finding", f.get("finding_id", "")[:14], name])
    for name in state.knowledge.get("reports", {}):
        rows.append(["knowledge", "knowledge", name])
    for b in state.decision_support.get("bundles", []):
        for name in b.get("reports", {}):
            rows.append(["decision", b.get("case_id", "")[:14], name])
    return rows


def report_pages(state) -> list:
    rows = _collect(state)
    by_domain: dict = {}
    for domain, _, _ in rows:
        by_domain[domain] = by_domain.get(domain, 0) + 1

    # Intelligence reports are validation-bearing artifacts, summarized here.
    intel = state.intelligence
    intel_reports = []
    for key in ("analytics", "trend", "quality", "summary"):
        art = intel.get(key, {})
        if art:
            intel_reports.append(["intelligence", key,
                                  art.get("validation", {}).get("ok")])

    sections = [
        kv_panel("Report Center", {
            "total_reports": len(rows) + len(intel_reports),
            "domains": sorted(by_domain),
        }),
        table("Reports by Domain", ["domain", "count"], sorted(by_domain.items())),
        table("Registered Reports", ["domain", "owner", "report"], rows),
        table("Intelligence / Validation Reports", ["domain", "report", "valid"], intel_reports),
    ]
    return [Page("reports", "Reports", sections, [])]
