"""Tests for the offline research application (V1-P8).

Covers: state loading from registered artifacts, the five workflows, visualization
specs, app-consistency validation, deterministic static HTML rendering, and that
the app sources everything from registered artifacts (presentation only).
"""

from __future__ import annotations

import pytest

from frontend.offline_research_app import (
    AppState, build_app_view, AppValidator, render_from_run_dir, render_app_html,
    upload_workflow, dataset_intelligence_workflow, inference_workflow,
    benchmark_workflow, audit_workflow,
)


@pytest.fixture(scope="module")
def app_state(offline_run):
    _, out = offline_run
    return AppState.load(out)


def test_state_loads_registered_artifacts(app_state):
    assert app_state.index["inference_id"]
    assert set(app_state.outputs) >= {"prediction", "probability", "calibration",
                                      "conformal", "coverage", "risk", "clinical", "summary"}
    assert app_state.dataset_intelligence.get("profile")
    assert app_state.current_inference()["validation_ok"] is True


def test_five_workflows_build_pages(app_state):
    pages = {
        "upload": upload_workflow(app_state),
        "dataset": dataset_intelligence_workflow(app_state),
        "inference": inference_workflow(app_state),
        "benchmark": benchmark_workflow(app_state),
        "audit": audit_workflow(app_state),
    }
    for pid, page in pages.items():
        d = page.to_dict()
        assert d["id"] == pid
        assert d["sections"], f"{pid} has no sections"
        assert d["visualizations"], f"{pid} has no visualizations"


def test_inference_workflow_shows_uncertainty(app_state):
    page = inference_workflow(app_state).to_dict()
    titles = {s["title"] for s in page["sections"]}
    # faithful uncertainty (NR-4): calibration + conformal + coverage + risk present
    assert {"Calibration", "Conformal", "Coverage", "Risk"}.issubset(titles)
    viz_types = {v["type"] for v in page["visualizations"]}
    assert "line" in viz_types  # calibration curve


def test_audit_workflow_shows_lineage_graph(app_state):
    page = audit_workflow(app_state).to_dict()
    viz = {v["title"]: v for v in page["visualizations"]}
    assert "Lineage Graph" in viz
    assert viz["Lineage Graph"]["spec"]["nodes"]  # non-empty lineage graph


def test_app_validation_passes(app_state):
    report = AppValidator().validate(app_state)
    assert report.ok is True
    names = {c.name for c in report.checks}
    assert {"artifact_consistency", "registry_consistency", "output_consistency",
            "version_consistency", "lineage_consistency"} == names


def test_build_app_view_has_five_pages(app_state):
    view = build_app_view(app_state).to_dict()
    assert [p["id"] for p in view["pages"]] == ["upload", "dataset", "inference",
                                                "benchmark", "audit"]
    assert view["validation"]["ok"] is True
    assert view["meta"]["source"].startswith("registered artifacts")


def test_html_render_is_deterministic_and_offline(offline_run):
    _, out = offline_run
    html1 = render_from_run_dir(out)
    html2 = render_from_run_dir(out)
    assert html1 == html2                      # deterministic (no timestamps)
    assert "<svg" in html1                      # inline charts
    assert "http://" not in html1 and "https://" not in html1  # no external assets
    assert "<script" not in html1               # no JavaScript (CSS-only tabs)
    assert html1.count("class='tab'") == 5      # five workflow tabs


def test_app_reflects_registered_values_only(app_state):
    """The displayed headline must equal the registered summary artifact value."""
    page = inference_workflow(app_state).to_dict()
    headline_section = next(s for s in page["sections"] if s["title"] == "Headline")
    registered = app_state.outputs["summary"]["headline"]
    assert headline_section["data"]["pairs"]["macro_f1"] == round(registered["macro_f1"], 4)
