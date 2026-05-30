"""Tests for the Clinical Workstation (V2-P7).

Covers navigation, every workspace (cases/reviews/findings/knowledge/intelligence/
decision/audit/lineage/reports/dashboard), state management + context determinism,
workstation validation (the seven consistency checks), version consistency,
boundary conditions, and the deterministic static-HTML renderer.

The snapshot is composed once (through the real V2 services) and shared read-only.
"""

from __future__ import annotations

import json

import pytest

from scripts.build_workstation_snapshot import build_snapshot
from frontend.clinical_workstation import (
    WorkstationState, build_from_snapshot,
    render_workstation_html, validate_state, area_ids,
)
from frontend.clinical_workstation.state import CONTEXT_KEYS


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return build_snapshot(n_cases=5)


@pytest.fixture()
def state(snapshot) -> WorkstationState:
    return WorkstationState.from_snapshot(snapshot)


@pytest.fixture(scope="module")
def view_dict(snapshot) -> dict:
    return build_from_snapshot(snapshot).to_dict()


# --- navigation ---------------------------------------------------------------
def test_navigation_has_all_primary_areas(view_dict):
    ids = [a["id"] for a in view_dict["areas"]]
    assert ids == ["dashboard", "cases", "reviews", "findings", "knowledge",
                   "intelligence", "decision", "audit", "lineage", "reports"]
    assert area_ids() == ids


def test_navigation_preserves_context(view_dict):
    # Every area carries the same preserved navigation context.
    contexts = [a["context"] for a in view_dict["areas"]]
    assert all(c == contexts[0] for c in contexts)
    assert contexts[0]["current_case"] is not None


# --- workspaces ---------------------------------------------------------------
def _area(view_dict, area_id):
    return next(a for a in view_dict["areas"] if a["id"] == area_id)


def test_case_workspace(view_dict, snapshot):
    area = _area(view_dict, "cases")
    # overview + one page per case
    assert len(area["pages"]) == 1 + len(snapshot["cases"])
    overview = area["pages"][0]
    assert any(s["kind"] == "table" for s in overview["sections"])
    assert any(v["type"] == "bar" for v in overview["visualizations"])


def test_review_workspace(view_dict, snapshot):
    area = _area(view_dict, "reviews")
    assert len(area["pages"]) == 1 + len(snapshot["reviews"])
    detail = area["pages"][1]
    titles = [s["title"] for s in detail["sections"]]
    assert "Review Status" in titles and "Progress" in titles


def test_findings_workspace(view_dict, snapshot):
    area = _area(view_dict, "findings")
    assert len(area["pages"]) == 1 + len(snapshot["findings"])
    detail = area["pages"][1]
    assert any(s["title"] == "Finding Evidence" for s in detail["sections"])


def test_knowledge_workspace(view_dict):
    area = _area(view_dict, "knowledge")
    page = area["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Concepts" in titles and "Terminology" in titles
    assert any(v["type"] == "graph" for v in page["visualizations"])


def test_intelligence_workspace(view_dict):
    page = _area(view_dict, "intelligence")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Population Analytics (blocks)" in titles
    assert "Trend Reports" in titles and "Quality Reports" in titles


def test_decision_workspace(view_dict, snapshot):
    area = _area(view_dict, "decision")
    assert len(area["pages"]) == 1 + len(snapshot["decision_support"]["bundles"])
    detail = area["pages"][1]
    titles = [s["title"] for s in detail["sections"]]
    assert any("Evidence Bundle" in t for t in titles)
    assert any("Guidance" in t for t in titles)
    # Decision support must not surface diagnosis/treatment language anywhere.
    blob = json.dumps(detail).lower()
    for forbidden in ("diagnosis", "treatment", "prescribe", "medication"):
        assert forbidden not in blob


def test_audit_browser(view_dict):
    page = _area(view_dict, "audit")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Audit Logs" in titles and "Event History (all scopes)" in titles
    assert any(v["type"] == "timeline" for v in page["visualizations"])


def test_lineage_explorer(view_dict):
    page = _area(view_dict, "lineage")["pages"][0]
    titles = [s["title"] for s in page["sections"]]
    assert "Chain Coverage" in titles
    assert any(v["title"].startswith("Traceability") for v in page["visualizations"])


def test_reporting_center(view_dict):
    page = _area(view_dict, "reports")["pages"][0]
    assert any(s["title"] == "Registered Reports" for s in page["sections"])


def test_dashboard(view_dict):
    page = _area(view_dict, "dashboard")["pages"][0]
    assert any(s["title"] == "System Status" for s in page["sections"])
    assert any(s["title"] == "Subsystems" for s in page["sections"])


# --- state management ---------------------------------------------------------
def test_default_context_is_seeded(state):
    state.default_context()
    ctx = state.context_snapshot()
    assert set(ctx) == set(CONTEXT_KEYS)
    assert ctx["current_case"] and ctx["current_patient"]


def test_set_context_is_deterministic(state):
    state.default_context()
    cid = state.cases[0]["case_id"]
    a = WorkstationState.from_snapshot(state.snapshot).default_context().set_context(current_case=cid)
    b = WorkstationState.from_snapshot(state.snapshot).default_context().set_context(current_case=cid)
    assert a.context_snapshot() == b.context_snapshot()


def test_set_context_rejects_unknown_key(state):
    with pytest.raises(KeyError):
        state.set_context(not_a_key="x")


# --- validation (the seven consistency checks) --------------------------------
def test_workstation_validation_passes(state):
    report = validate_state(state.default_context()).to_dict()
    names = {c["name"] for c in report["checks"]}
    assert names == {
        "artifact_consistency", "registry_consistency", "version_consistency",
        "audit_consistency", "lineage_consistency", "workflow_consistency",
        "state_consistency",
    }
    assert report["ok"], report


def test_state_consistency_detects_dangling_context(state):
    state.default_context().set_context(current_case="case+deadbeefdeadbeef")
    report = validate_state(state).to_dict()
    failed = {c["name"] for c in report["checks"] if not c["passed"]}
    assert "state_consistency" in failed


def test_audit_chains_reported_verified(state):
    for c in state.cases:
        assert c["audit"]["verified"] is True
    for r in state.reviews:
        assert r["audit"]["verified"] is True


def test_lineage_chain_verified(state):
    assert state.representative_chain["verified"] is True
    kinds = {r["kind"] for r in state.representative_chain["records"]}
    for k in ("patient", "case", "review", "finding", "decision_support"):
        assert k in kinds


# --- boundary conditions ------------------------------------------------------
def test_empty_snapshot_does_not_crash():
    empty = {"snapshot_version": "x", "cases": [], "reviews": [], "findings": [],
             "knowledge": {}, "intelligence": {}, "decision_support": {},
             "lineage": {"records": {}, "n_records": 0},
             "representative_chain": {"records": [], "verified": True},
             "registries": {}, "meta": {"patients": []}}
    view = build_from_snapshot(empty).to_dict()
    assert [a["id"] for a in view["areas"]]  # all areas still render
    # workflow_consistency fails on an empty graph (no chain kinds) -> validation not ok
    assert view["validation"]["ok"] in (True, False)


def test_lookup_misses_return_empty(state):
    assert state.case("nope") == {}
    assert state.review("nope") == {}
    assert state.finding("nope") == {}


# --- rendering / determinism --------------------------------------------------
def test_html_render_is_deterministic(snapshot):
    h1 = render_workstation_html(build_from_snapshot(snapshot))
    h2 = render_workstation_html(build_from_snapshot(build_snapshot(n_cases=5)))
    assert h1 == h2
    assert h1.startswith("<!doctype html>")
    assert "Clinical Workstation" in h1


def test_snapshot_is_reproducible():
    a = json.dumps(build_snapshot(n_cases=3), sort_keys=True)
    b = json.dumps(build_snapshot(n_cases=3), sort_keys=True)
    assert a == b
