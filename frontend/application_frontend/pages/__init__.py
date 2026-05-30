"""``frontend/application_frontend/pages`` — page view-model builders (P7-D…H).

Each builder assembles a deterministic Page dict (id, title, nav, flash, sections) from
the current state snapshot + backend-sourced view data. No I/O, no domain imports.
"""

from __future__ import annotations

import json
from typing import Optional

from .. import components as C
from ..forms import LOGIN_FORM, REGISTRATION_FORM, UPLOAD_FORM


def _page(page_id: str, title: str, snapshot: dict, sections: list, *,
          subtitle: str = "") -> dict:
    flash = snapshot.get("flash", {"level": "", "message": ""})
    page = {"id": page_id, "title": title, "subtitle": subtitle,
            "nav": C.nav(snapshot), "sections": list(sections),
            "flash": flash if flash.get("message") else None}
    return page


# --- auth pages --------------------------------------------------------------
def login_page(snapshot: dict, *, field_errors=()) -> dict:
    sections = []
    if snapshot.get("session_expired"):
        sections.append(C.alert("warning", "Your session has expired. Please log in again."))
    sections.append(C.form_section("Log in", LOGIN_FORM.to_dict(), field_errors))
    sections.append(C.prose("New here?", "Create an account from the Register page."))
    return _page("login", "NeuroVision — Log in", snapshot, sections,
                 subtitle="Sign in to upload EEG and run analyses.")


def register_page(snapshot: dict, *, field_errors=()) -> dict:
    return _page("register", "NeuroVision — Create account", snapshot,
                 [C.form_section("Create account", REGISTRATION_FORM.to_dict(), field_errors)],
                 subtitle="Local account — clinician, researcher, or viewer.")


# --- dashboard (P7-D) --------------------------------------------------------
def dashboard_page(snapshot: dict) -> dict:
    user = snapshot.get("user") or {}
    uploads = snapshot.get("uploads", [])
    workflows = snapshot.get("workflows", [])
    sections = [
        C.kv("User summary", [
            ("Username", user.get("username")), ("User id", user.get("user_id")),
            ("Roles", ", ".join(user.get("roles", [])) or "—"),
            ("Session", (snapshot.get("session") or {}).get("session_id")),
        ]),
        C.kv("System status", [
            ("Uploads", len(uploads)), ("Analyses", len(workflows)),
            ("Predictions available", len(snapshot.get("predictions", {}))),
            ("Backend API", "v1 (connected)"),
        ]),
        C.table("Recent uploads", ["Upload", "File", "Status"],
                [[u["upload_id"], u["filename"], u["status"]] for u in uploads[-5:]] or [["—", "—", "—"]]),
        C.table("Recent analyses", ["Analysis", "Status", "Prediction"],
                [[w["analysis_id"], w["status"], w["prediction_id"]] for w in workflows[-5:]]
                or [["—", "—", "—"]]),
        C.table("Recent predictions", ["Analysis", "Label", "Confidence"],
                [[a, p.get("predicted_label"), p.get("confidence_level")]
                 for a, p in list(snapshot.get("predictions", {}).items())[-5:]] or [["—", "—", "—"]]),
    ]
    return _page("dashboard", "Dashboard", snapshot, sections,
                 subtitle="Your recent activity, sourced from the backend.")


# --- upload (P7-E) -----------------------------------------------------------
def upload_page(snapshot: dict, *, field_errors=()) -> dict:
    uploads = snapshot.get("uploads", [])
    sections = [
        C.form_section("Upload an EEG recording", UPLOAD_FORM.to_dict(), field_errors),
        C.prose("Supported formats",
                "Whatever the backend EEG Foundation accepts (EDF, EDF+, BDF, BDF+, FIF, SET). "
                "Validation findings are reported by the backend."),
        C.table("Upload history", ["Upload", "File", "Fingerprint", "Bytes", "Status"],
                [[u["upload_id"], u["filename"], u["content_fingerprint"][:12],
                  u["size_bytes"], u["status"]] for u in uploads] or [["—", "—", "—", "—", "—"]]),
    ]
    return _page("upload", "Upload EEG", snapshot, sections,
                 subtitle="Send a real recording to the platform.")


# --- analysis (P7-F) ---------------------------------------------------------
def analysis_page(snapshot: dict, *, stage_view=None) -> dict:
    workflows = snapshot.get("workflows", [])
    sections = []
    if stage_view:
        sections.append(C.stages("Workflow progress", stage_view))
    sections.append(C.table(
        "Analysis history", ["Analysis", "Workflow", "Status", "Prediction"],
        [[w["analysis_id"], w["workflow_id"], w["status"], w["prediction_id"]] for w in workflows]
        or [["—", "—", "—", "—"]]))
    if not workflows:
        sections.insert(0, C.prose("No analyses yet",
                                   "Upload an EEG, then start an analysis to generate a prediction."))
    return _page("analysis", "Analysis", snapshot, sections,
                 subtitle="Start an analysis and follow the backend workflow.")


# --- prediction (P7-G) -------------------------------------------------------
def prediction_page(snapshot: dict, view: Optional[dict]) -> dict:
    if not view:
        return _page("prediction", "Prediction", snapshot,
                     [C.prose("No prediction selected", "Run an analysis to view a prediction.")])
    probs = view.get("class_probabilities", [])
    sections = [
        C.kv("Prediction", [
            ("Label", view.get("predicted_label")), ("Class", view.get("predicted_class")),
            ("Model", view.get("model_id")),
        ]),
        C.kv("Uncertainty (always shown)", [
            ("Confidence level", view.get("confidence_level")),
            ("Confidence score", view.get("confidence_score")),
            ("Calibration", view.get("calibration_quality")),
        ]),
        C.table("Class probabilities", ["Class", "Label", "Probability"],
                [[p.get("class"), p.get("label"), p.get("probability")] for p in probs]
                or [["—", "—", "—"]]),
        C.kv("Explanation summary", [
            ("Method", view.get("explanation_method")),
            ("Top factors", len(view.get("top_factors", []))),
        ]),
    ]
    return _page("prediction", "Prediction", snapshot, sections,
                 subtitle=f"Analysis {view.get('analysis_id', '')}")


# --- reports (P7-H) ----------------------------------------------------------
def reports_page(snapshot: dict, view: Optional[dict], reports: Optional[list] = None) -> dict:
    if not view:
        return _page("reports", "Reports", snapshot,
                     [C.prose("No reports", "Run an analysis to generate reports.")])
    sections = [
        C.items_list("Available reports", view.get("report_names", [])),
        C.kv("Validation summary", [
            ("Workflow audit verified", view["validation_summary"].get("workflow_audit_verified")),
            ("Lineage chain verified", view["validation_summary"].get("lineage_chain_verified")),
        ]),
        C.kv("Audit summary", [
            ("Audit events", view["audit_summary"].get("n_audit_events")),
            ("Audit head", (view["audit_summary"].get("audit_head") or "")[:16]),
        ]),
    ]
    for r in (reports or []):
        sections.append(C.report_section(
            f"Report: {r.name}", r.name, r.content,
            json.dumps(r.content, indent=2, sort_keys=True, default=str)))
    return _page("reports", "Reports", snapshot, sections,
                 subtitle="View and download analysis reports.")


__all__ = [
    "login_page", "register_page", "dashboard_page", "upload_page", "analysis_page",
    "prediction_page", "reports_page",
]
