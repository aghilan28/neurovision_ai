"""Workflow workspace — registry, transitions, dependencies, bottlenecks, efficiency."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import workflow_flow, dependency_network


def _overview(state) -> Page:
    block = state.workflows
    registry = block.get("registry", {})
    workflows = state.workflow_records
    rows = [[w.get("workflow_id", "")[:18], w.get("workflow_type"), w.get("subject_kind"),
             w.get("state"), len(w.get("bottlenecks", [])), w.get("lineage_verified")]
            for w in workflows]
    sections = [
        kv_panel("Workflow Registry", {
            "n_workflows": block.get("n_workflows"),
            "workflow_registry_version": registry.get("workflow_registry_version"),
            "audit_verified": block.get("audit", {}).get("verified"),
        }),
        badges("Workflow Validation",
               [((w.get("subject_id") or w.get("workflow_id", ""))[:14],
                 w.get("validation", {}).get("ok", False)) for w in workflows]),
        table("Workflows", ["id", "type", "subject", "state", "bottlenecks", "lineage_ok"], rows),
    ]
    return Page("workflows-overview", "Workflows", sections, [])


def _detail(w: dict) -> Page:
    reports = w.get("reports", {})
    eff = reports.get("efficiency_report", {}).get("metrics", [])
    eff_rows = [[m.get("name"), round(float(m.get("value", 0.0)), 4), m.get("unit", "")]
                for m in eff]
    sections = [
        kv_panel("Workflow", {
            "workflow_id": w.get("workflow_id"), "type": w.get("workflow_type"),
            "subject": w.get("subject_id"), "state": w.get("state"),
            "version": (w.get("version") or "")[:12],
        }),
        badges("Bottlenecks",
               [(b, "fail") for b in w.get("bottlenecks", [])] or [("none detected", "pass")]),
        table("Efficiency Metrics", ["metric", "value", "unit"], eff_rows),
    ]
    viz = [workflow_flow(w), dependency_network(w)]
    return Page(f"workflow-{w.get('workflow_id', '')[:12]}",
                f"Workflow {(w.get('subject_id') or '')[:14]}", sections, viz)


def workflow_pages(state) -> list:
    pages = [_overview(state)]
    for w in state.workflow_records:
        pages.append(_detail(w))
    return pages
