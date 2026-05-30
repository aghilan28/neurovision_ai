"""Frontend meta-reports (P7-L) — deterministic, version-tagged.

Builds the Frontend Validation / Workflow / State / Integration reports. Each is a plain,
deterministic JSON-able dict (no wall-clock, no randomness, no secrets). These describe
the *presentation layer's* behaviour; they reference backend artifact ids but contain no
backend business data of their own.
"""

from __future__ import annotations

from typing import Optional

from .gateway import ALL_OPERATIONS
from .util import fingerprint
from .version import APPLICATION_FRONTEND_VERSION, FRONTEND_REPORT_VERSION


def _header(report_type: str) -> dict:
    return {"report_type": report_type, "frontend_report_version": FRONTEND_REPORT_VERSION,
            "application_frontend_version": APPLICATION_FRONTEND_VERSION}


def build_frontend_validation_report(validation_report) -> dict:
    return {**_header("frontend_validation"), "ok": validation_report.ok,
            "validation": validation_report.to_dict()}


def build_frontend_workflow_report(state) -> dict:
    snap = state.snapshot()
    return {
        **_header("frontend_workflow"),
        "n_workflows": len(snap["workflows"]), "workflows": snap["workflows"],
        "n_uploads": len(snap["uploads"]),
        "n_predictions": len(snap["predictions"]),
    }


def build_frontend_state_report(state) -> dict:
    snap = state.snapshot()
    return {**_header("frontend_state"), "state_signature": fingerprint(snap),
            "current_page": snap["current_page"], "authenticated": snap["authenticated"],
            "snapshot": snap}


def build_frontend_integration_report(state, operations_exercised: Optional[list] = None) -> dict:
    exercised = sorted(set(operations_exercised or []))
    snap = state.snapshot()
    return {
        **_header("frontend_integration"),
        "consumes_api_version": "v1",
        "operations_available": list(ALL_OPERATIONS),
        "operations_exercised": exercised,
        "all_exercised": set(exercised) == set(ALL_OPERATIONS),
        "evidence": {
            "authenticated": snap["authenticated"],
            "has_uploads": len(snap["uploads"]) > 0,
            "has_workflows": len(snap["workflows"]) > 0,
            "has_predictions": len(snap["predictions"]) > 0,
            "has_reports": len(snap["reports"]) > 0,
        },
    }


def build_all_reports(app, *, validation_report=None, operations_exercised=None) -> dict:
    reports = {
        "frontend_workflow_report": build_frontend_workflow_report(app.state),
        "frontend_state_report": build_frontend_state_report(app.state),
        "frontend_integration_report": build_frontend_integration_report(
            app.state, operations_exercised),
    }
    if validation_report is not None:
        reports["frontend_validation_report"] = build_frontend_validation_report(validation_report)
    return reports


__all__ = [
    "build_frontend_validation_report", "build_frontend_workflow_report",
    "build_frontend_state_report", "build_frontend_integration_report", "build_all_reports",
]
