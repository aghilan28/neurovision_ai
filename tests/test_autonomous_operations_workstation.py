"""Tests for the Autonomous Operations Workstation (V4-P8).

Verifies the human-oversight workstation is a coherent, fully-traceable, fully-
registered presentation layer over the composed Version 4 platform + the V4-P7
Governance Intelligence Layer, with governed intervention controls. Driven from the
deterministic snapshot built by ``_v4d_helpers.build_aow_snapshot``.
"""

from __future__ import annotations

import pytest

from _v4d_helpers import build_v4d, build_aow_snapshot

from frontend.autonomous_operations_workstation import (
    WorkstationState, build_from_snapshot, validate_state,
    build_controls, controls_summary, area_ids, InterventionControl,
)


@pytest.fixture(scope="module")
def snapshot():
    return build_aow_snapshot(build_v4d(2))


@pytest.fixture(scope="module")
def view(snapshot):
    return build_from_snapshot(snapshot).to_dict()


# --- navigation ---------------------------------------------------------------
def test_eleven_primary_areas(view):
    ids = [a["id"] for a in view["areas"]]
    assert ids == ["system-health", "goals", "policies", "plans", "tasks", "agents",
                   "executions", "governance", "audit", "lineage", "reports"]
    assert ids == area_ids()


def test_every_area_has_pages_and_context(view):
    for area in view["areas"]:
        assert area["pages"], f"{area['id']} has no pages"
        # context preserved across areas (the nine context keys present)
        assert "current_goal" in area["context"] and "current_governance" in area["context"]


# --- per-entity workspaces ----------------------------------------------------
@pytest.mark.parametrize("area_id", ["goals", "policies", "plans", "tasks", "agents",
                                     "executions"])
def test_entity_workspaces_render(view, area_id):
    area = next(a for a in view["areas"] if a["id"] == area_id)
    page = area["pages"][0]
    assert page["sections"]
    # a registry table with at least one row
    tables = [s for s in page["sections"] if s["kind"] == "table"]
    assert tables and any(t["data"]["rows"] for t in tables)


def test_agent_workspace_has_suspend_controls(view):
    area = next(a for a in view["areas"] if a["id"] == "agents")
    actions = {c["action"] for p in area["pages"] for c in p["controls"]}
    assert "suspend_agent" in actions


def test_execution_workspace_has_intervention_controls(view):
    area = next(a for a in view["areas"] if a["id"] == "executions")
    actions = {c["action"] for p in area["pages"] for c in p["controls"]}
    assert {"pause_execution", "terminate_execution", "escalate_approval",
            "request_review"} <= actions


# --- governance workspace -----------------------------------------------------
def test_governance_workspace(view):
    area = next(a for a in view["areas"] if a["id"] == "governance")
    page_ids = {p["id"] for p in area["pages"]}
    assert {"governance-health", "governance-approvals", "governance-violations",
            "governance-escalations", "governance-risk"} <= page_ids


# --- audit browser ------------------------------------------------------------
def test_audit_browser(view, snapshot):
    area = next(a for a in view["areas"] if a["id"] == "audit")
    page = area["pages"][0]
    # the unified audit summary should report all logs verified
    kv = next(s for s in page["sections"] if s["kind"] == "kv")
    assert kv["data"]["all_verified"] is True
    # one badge per subsystem audit log (entities + governance)
    badge_section = next(s for s in page["sections"] if s["kind"] == "badges")
    assert len(badge_section["data"]["badges"]) >= 7


# --- lineage explorer ---------------------------------------------------------
def test_lineage_explorer_spine_present(view):
    area = next(a for a in view["areas"] if a["id"] == "lineage")
    page = area["pages"][0]
    badges = next(s for s in page["sections"] if s["kind"] == "badges")
    spine = {b["label"]: b["value"] for b in badges["data"]["badges"]}
    for kind in ("patient", "goal", "policy", "plan", "task", "agent", "execution",
                 "governance_intelligence"):
        assert spine.get(kind) is True
    # the traceability graph has no dangling edges
    graph = next(v for v in page["visualizations"] if v["type"] == "graph")
    node_ids = {n["id"] for n in graph["spec"]["nodes"]}
    for e in graph["spec"]["edges"]:
        assert e["from"] in node_ids and e["to"] in node_ids


# --- report center ------------------------------------------------------------
def test_report_center_lists_all_subsystems(view):
    area = next(a for a in view["areas"] if a["id"] == "reports")
    page = area["pages"][0]
    table = next(s for s in page["sections"] if s["kind"] == "table")
    subsystems = {row[0] for row in table["data"]["rows"]}
    assert {"goals", "policies", "plans", "tasks", "agents", "executions",
            "governance"} <= subsystems


# --- intervention controls ----------------------------------------------------
def test_intervention_controls_are_governed(snapshot):
    state = WorkstationState.from_snapshot(snapshot)
    controls = build_controls(state)
    assert controls
    for c in controls:
        cd = c.to_dict() if isinstance(c, InterventionControl) else c
        assert cd["requires_authorization"]
        assert cd["generates_audit"] and cd["generates_lineage"]
        assert cd["generates_governance_record"]
    summary = controls_summary(controls)
    assert summary["all_governed"]


# --- state management ---------------------------------------------------------
def test_state_context_is_deterministic_and_referential(snapshot):
    state = WorkstationState.from_snapshot(snapshot).default_context()
    ctx = state.context_snapshot()
    assert state.record("goals", ctx["current_goal"])
    assert state.record("executions", ctx["current_execution"])
    # setting an unknown context key is rejected
    with pytest.raises(KeyError):
        state.set_context(bogus="x")


# --- workstation validation ---------------------------------------------------
def test_validation_all_consistency_checks_pass(snapshot):
    state = WorkstationState.from_snapshot(snapshot).default_context()
    report = validate_state(state)
    assert report.ok, report.to_dict()
    names = {c.name for c in report.checks}
    assert {"registry_consistency", "audit_consistency", "lineage_consistency",
            "visualization_consistency", "report_consistency", "state_consistency"} <= names


# --- determinism --------------------------------------------------------------
def test_view_is_deterministic():
    a = build_from_snapshot(build_aow_snapshot(build_v4d(2))).to_dict()
    b = build_from_snapshot(build_aow_snapshot(build_v4d(2))).to_dict()
    assert a == b
