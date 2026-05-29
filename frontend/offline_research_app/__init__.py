"""``frontend/offline_research_app`` — Offline Research Application (V1-P8).

A presentation-only research workstation. It loads the backend's **registered
artifacts** (JSON) and renders them as view-models + a static, offline HTML report.
It imports **no domain module** (no ml/evaluation/datasets/preprocessing/backend) —
stdlib only — which is the platform's strictest boundary (NR-8). Every value shown
originates from a registered artifact; the UI computes nothing.

Public surface:
  * ``AppState.load(run_dir)``   — load registered artifacts.
  * ``build_app_view(state)``    — assemble the 5-workflow application view-model.
  * ``render_from_run_dir(dir)`` — render the static offline HTML report.
  * ``AppValidator``             — app-consistency validation.
"""

from __future__ import annotations

from .version import OFFLINE_RESEARCH_APP_VERSION, VIEWMODEL_VERSION, VISUALIZATION_VERSION
from .schemas import Section, Visualization, Page, AppView, ValidationReport
from .state import AppState
from .pages import build_app_view
from .validation import AppValidator
from .workflows import (
    upload_workflow, dataset_intelligence_workflow, inference_workflow,
    benchmark_workflow, audit_workflow, all_workflows,
)
from .reports import render_app_html, render_from_run_dir, write_app_html

__all__ = [
    "OFFLINE_RESEARCH_APP_VERSION", "VIEWMODEL_VERSION", "VISUALIZATION_VERSION",
    "Section", "Visualization", "Page", "AppView", "ValidationReport",
    "AppState", "build_app_view", "AppValidator",
    "upload_workflow", "dataset_intelligence_workflow", "inference_workflow",
    "benchmark_workflow", "audit_workflow", "all_workflows",
    "render_app_html", "render_from_run_dir", "write_app_html",
]
