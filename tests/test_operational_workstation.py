"""Tests for the Operational Intelligence Workstation (V3-P7).

Covers navigation, every workspace (system-health/events/timelines/workflows/graph/
analytics/recommendations/audit/lineage/reports), state management + context
determinism, workstation validation (the six consistency checks), boundary
conditions, and the deterministic static-HTML renderer.

The snapshot is composed once (through the real V3 services) and shared read-only.
"""

from __future__ import annotations

import json

import pytest

from scripts.build_operational_workstation_snapshot import build_snapshot
from frontend.operational_workstation import (
    WorkstationState, build_from_snapshot,
    render_workstation_html, validate_state, area_ids,
)
from frontend.operational_workstation.state import CONTEXT_KEYS


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return build_snapshot(n_cases=3)


@pytest.fixture()
def state(snapshot) -> WorkstationState:
    return WorkstationState.from_snapshot(snapshot)


@pytest.fixture(scope="module")
def view_dict(snapshot) -> dict:
    return build_from_snapshot(snapshot).to_dict()


def _area(view_dict, area_id):
    return next(a for a in view_dict["areas"] if a["id"] == area_id)


# --- navigation ---------------------------------------------------------------
def test_navigation_has_all_primary_areas(view_dict):
    ids = [a["id"] for a in view_dict["areas"]]
    assert ids == ["system-health", "events", "timelines", "workflows", "graph",
                   "analytics", "recommendations", "audit", "lineage", "reports"]
    assert area_ids() == ids


def test_navigation_preserves_context(view_dict):
    contexts = [a["context"] for a in view_dict["areas"]]
    assert all(c == contexts[0] for c in contexts)
    assert contexts[0]["current_event"] is not None
    assert contexts[0]["current_recommendation"] is not None


# --- workspaces ---------------------------------------------------------------
def test_event_workspace(view_dict):
    page = _area(view_dict, "events")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Event Registry" in titles and "Event Taxonomy" in titles
    assert any(v["type"] == "timeline" for v in page["visualizations"])
    assert any(v["type"] == "bar" for v in page["visualizations"])


def test_timeline_workspace(view_dict):
    page = _area(view_dict, "timelines")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Temporal Registry" in titles
    assert any("Temporal Analytics" in t for t in titles)


def test_workflow_workspace(view_dict, snapshot):
    area = _area(view_dict, "workflows")
    # overview + one page per workflow
    assert len(area["pages"]) == 1 + len(snapshot["workflows"]["workflows"])
    detail = area["pages"][1]
    titles = [s["title"] for s in detail["sections"]]
    assert "Efficiency Metrics" in titles and "Bottlenecks" in titles
    assert any(v["type"] == "graph" for v in detail["visualizations"])


def test_graph_workspace(view_dict):
    page = _area(view_dict, "graph")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Node Registry (by type)" in titles and "Edge Registry (by type)" in titles
    assert any(v["title"].startswith("Operational Graph") for v in page["visualizations"])


def test_analytics_workspace(view_dict):
    page = _area(view_dict, "analytics")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert {"Metrics", "Health Scores", "Performance", "Quality", "Risk Scores"} <= set(titles)


def test_recommendation_workspace(view_dict):
    page = _area(view_dict, "recommendations")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Recommendations" in titles
    assert any("Escalation Candidates" in t for t in titles)
    # operational-only: every recommendation is guidance/optimization/escalation
    reg = next(s for s in page["sections"] if s["title"] == "Recommendation Registry")
    pairs = reg["data"]["pairs"]
    assert pairs["guidance"] + pairs["optimization"] + pairs["escalation"] == \
        pairs["n_recommendations"]


def test_audit_browser(view_dict):
    page = _area(view_dict, "audit")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Audit Logs" in titles and "Event History (all subsystems)" in titles
    assert any(v["type"] == "timeline" for v in page["visualizations"])


def test_lineage_explorer(view_dict):
    page = _area(view_dict, "lineage")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Chain Coverage" in titles
    assert any(v["title"].startswith("Traceability") for v in page["visualizations"])
    # the full chain coverage table marks every mandated stage present
    coverage = next(s for s in page["sections"] if s["title"] == "Chain Coverage")
    assert all(row[2] for row in coverage["data"]["rows"]), coverage["data"]["rows"]


def test_report_center(view_dict):
    page = _area(view_dict, "reports")["pages"][0]
    assert any(s["title"] == "Registered Reports" for s in page["sections"])


def test_system_health(view_dict):
    page = _area(view_dict, "system-health")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "System Health" in titles and "Subsystem Status (audit verified)" in titles


# --- state management ---------------------------------------------------------
def test_default_context_is_seeded(state):
    state.default_context()
    ctx = state.context_snapshot()
    assert set(ctx) == set(CONTEXT_KEYS)
    assert ctx["current_event"] and ctx["current_workflow"] and ctx["current_recommendation"]


def test_set_context_is_deterministic(state):
    eid = state.event_records[0]["event_id"]
    a = WorkstationState.from_snapshot(state.snapshot).default_context().set_context(
        current_event=eid)
    b = WorkstationState.from_snapshot(state.snapshot).default_context().set_context(
        current_event=eid)
    assert a.context_snapshot() == b.context_snapshot()


def test_set_context_rejects_unknown_key(state):
    with pytest.raises(KeyError):
        state.set_context(not_a_key="x")


# --- validation (the six consistency checks) ----------------------------------
def test_workstation_validation_passes(state):
    report = validate_state(state.default_context()).to_dict()
    names = {c["name"] for c in report["checks"]}
    assert names == {
        "registry_consistency", "audit_consistency", "lineage_consistency",
        "visualization_consistency", "report_consistency", "state_consistency",
    }
    assert report["ok"], report


def test_state_consistency_detects_dangling_context(state):
    state.default_context().set_context(current_event="event+deadbeefdeadbeef")
    report = validate_state(state).to_dict()
    failed = {c["name"] for c in report["checks"] if not c["passed"]}
    assert "state_consistency" in failed


def test_audit_chains_reported_verified(state):
    for _, audit in state.audit_logs():
        assert audit["verified"] is True


def test_lineage_chain_verified(state):
    assert state.representative_chain["verified"] is True
    kinds = {r["kind"] for r in state.representative_chain["records"]}
    for k in ("patient", "case", "event", "workflow", "graph_node", "analytics",
              "recommendation"):
        assert k in kinds


# --- boundary conditions ------------------------------------------------------
def test_empty_snapshot_does_not_crash():
    empty = {"snapshot_version": "x", "events": {}, "timelines": {}, "workflows": {},
             "graph": {}, "analytics": {}, "recommendations": {},
             "lineage": {"records": {}, "n_records": 0},
             "representative_chain": {"records": [], "verified": True},
             "registries": {}, "meta": {}}
    view = build_from_snapshot(empty).to_dict()
    assert [a["id"] for a in view["areas"]] == area_ids()  # all areas still render
    assert view["validation"]["ok"] in (True, False)


def test_lookup_misses_return_empty(state):
    assert state.event("nope") == {}
    assert state.workflow("nope") == {}
    assert state.recommendation("nope") == {}


# --- rendering / determinism --------------------------------------------------
def test_html_render_is_deterministic(snapshot):
    h1 = render_workstation_html(build_from_snapshot(snapshot))
    h2 = render_workstation_html(build_from_snapshot(build_snapshot(n_cases=3)))
    assert h1 == h2
    assert h1.startswith("<!doctype html>")
    assert "Operational Intelligence Workstation" in h1
    assert "<script" not in h1  # no JavaScript (offline, deterministic)


def test_snapshot_is_reproducible():
    a = json.dumps(build_snapshot(n_cases=3), sort_keys=True)
    b = json.dumps(build_snapshot(n_cases=3), sort_keys=True)
    assert a == b
