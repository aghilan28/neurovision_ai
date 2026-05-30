"""Report center — surface every registered report across the V3 subsystems."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table


def _report_names(block: dict) -> list:
    return sorted((block or {}).get("reports", {}).keys())


def report_pages(state) -> list:
    # Per-workflow reports live inside each workflow record; count distinct kinds.
    wf_report_kinds = set()
    for w in state.workflow_records:
        wf_report_kinds.update((w.get("reports", {}) or {}).keys())

    rows = []
    rows += [["events", r] for r in _report_names(state.events)]
    rows += [["timelines", r] for r in _report_names(state.timelines)]
    rows += [["workflows", r] for r in sorted(wf_report_kinds)]
    rows += [["graph", r] for r in _report_names(state.graph)]
    rows += [["analytics", r] for r in _report_names(state.analytics)]
    rows += [["recommendations", r] for r in _report_names(state.recommendations)]

    sections = [
        kv_panel("Report Center", {
            "n_reports": len(rows),
            "subsystems": "events, timelines, workflows, graph, analytics, recommendations",
            "source": "registered reports only (presentation; no recomputation)",
        }),
        table("Registered Reports", ["subsystem", "report"], rows),
    ]
    return [Page("reports", "Reports", sections, [])]
