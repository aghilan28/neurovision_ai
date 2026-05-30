"""Report center (V4-P8) — every registered report across the Version 4 subsystems.

Goals, policies, plans, tasks, agents, executions, and governance-intelligence
reports, plus validation reports. Read-only: it lists and links the reports each
subsystem already registered into the snapshot; it never generates report content.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table


def report_pages(state) -> list:
    blocks = state.reports_blocks()          # list[(scope, reports_dict)]
    rows = []
    for scope, reports in blocks:
        for name in sorted(reports.keys()):
            rows.append([scope, name])
    n_reports = len(rows)

    sections = [
        kv_panel("Report Center", {
            "n_subsystems": len(blocks), "n_reports": n_reports,
            "subsystems": [scope for scope, _ in blocks],
        }),
        table("Registered Reports", ["subsystem", "report"], rows),
    ]
    return [Page("reports", "Reports", sections)]
