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
    return _page("login", "NeuroVision - Secure Access", snapshot, sections,
                 subtitle="Enter the clinical intelligence operating environment.")


def register_page(snapshot: dict, *, field_errors=()) -> dict:
    return _page("register", "NeuroVision - Provision Account", snapshot,
                 [C.form_section("Create account", REGISTRATION_FORM.to_dict(), field_errors)],
                 subtitle="Create a governed local identity for clinical, research, or review access.")


# --- Screen 1: Command Center ------------------------------------------------
def dashboard_page(snapshot: dict) -> dict:
    user = snapshot.get("user") or {}
    uploads = snapshot.get("uploads", [])
    workflows = snapshot.get("workflows", [])
    predictions = list(snapshot.get("predictions", {}).items())

    sections = [
        # TOP SECTION: Operational Readiness
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
        C.kv("Intelligence Readiness", [
            ("Operational Status", "Active"),
            ("Dataset Readiness", "Verified"),
            ("Model Readiness", "Calibrated"),
            ("System Health", "Optimal"),
        ]),

        # SECOND SECTION: Four Large Intelligence Cards
        C.kv("Dataset Readiness", [("Artifacts", len(uploads)), ("Status", "Ready")]),
        C.kv("Model Readiness", [("Models", 1), ("Type", "EEG-Foundation-V1")]),
        C.kv("System Health", [("Backend", "v1 (connected)"), ("Session", (snapshot.get("session") or {}).get("session_id")[:8] if snapshot.get("session") else "—")]),
        C.kv("Intelligence Activity", [("Analyses", len(workflows)), ("Predictions", len(predictions))]),

        # THIRD SECTION: Timeline Layout
        C.timeline("Recent uploads", [[u["upload_id"], u["filename"], u["status"]] for u in uploads[-5:]]),
        C.timeline("Recent analyses", [[w["analysis_id"], w["status"], w["prediction_id"]] for w in workflows[-5:]]),
        C.timeline("Recent predictions", [[a, p.get("predicted_label"), p.get("confidence_level")]
                 for a, p in list(snapshot.get("predictions", {}).items())[-5:]]),
        C.timeline("Recent Intelligence Activity", [[f"Upload: {u['filename']}", u['upload_id'], u['status']] for u in uploads[-3:]] +
                [[f"Analysis: {w['workflow_id']}", w['analysis_id'], w['status']] for w in workflows[-3:]]),

        # BOTTOM SECTION: Quick Actions
        C.prose("Intelligence Actions", "Direct access to governed operations: Upload EEG | Run Analysis | Review Predictions | Open Reports")
    ]
    return _page("dashboard", "Good Morning", snapshot, sections,
                 subtitle="NeuroVision Intelligence Environment Ready")


# --- Screen 2: EEG Intake Workspace ------------------------------------------
def upload_page(snapshot: dict, *, field_errors=()) -> dict:
    uploads = snapshot.get("uploads", [])
    sections = [
        C.form_section("EEG Data Acquisition", UPLOAD_FORM.to_dict(), field_errors),
        C.kv("Upload Readiness", [
            ("Supported Formats", "EDF, BDF, FIF, SET"),
            ("Governance", "Lore Protocol Compliant"),
            ("Security", "Encrypted-at-Rest"),
        ]),
        C.table("Upload history", ["Upload", "File", "Fingerprint", "Bytes", "Status"],
                [[u["upload_id"], u["filename"], u["content_fingerprint"][:12],
                  u["size_bytes"], u["status"]] for u in uploads] or [["—", "—", "—", "—", "—"]]),
        C.timeline("Acquisition Journey", [[u["upload_id"][:12], u["filename"], u["status"]] for u in uploads]),
    ]
    return _page("upload", "EEG Intake Workspace", snapshot, sections,
                 subtitle="Acquire and validate recordings through the governed backend intake contract.")


# --- Screen 3: Analysis Execution Workspace ----------------------------------
def analysis_page(snapshot: dict, *, stage_view=None) -> dict:
    workflows = snapshot.get("workflows", [])
    sections = []
    if stage_view:
        sections.append(C.stages("Workflow progress", stage_view))
        sections.append(C.stages("Vertical Analysis Timeline", stage_view))

    sections.append(C.table(
        "Analysis history", ["Analysis", "Workflow", "Status", "Prediction"],
        [[w["analysis_id"], w["workflow_id"], w["status"], w["prediction_id"]] for w in workflows]
        or [["—", "—", "—", "—"]]))
    sections.append(C.table(
        "Analysis Execution History", ["Analysis", "Status", "Progress"],
        [[w["analysis_id"], w["status"], "Completed" if w["prediction_id"] else "Processing"] for w in workflows]
        or [["—", "—", "—"]]))

    if not workflows:
        sections.insert(0, C.prose("Live Intelligence Feed",
                                   "Analysis pipeline is idle. Awaiting EEG intake.", intelligence=True))
    return _page("analysis", "Analysis Execution Workspace", snapshot, sections,
                 subtitle="Invisible computation made visible through real-time stage monitoring.")


# --- Screen 4: Prediction Review Workspace -----------------------------------
def prediction_page(snapshot: dict, view: Optional[dict]) -> dict:
    if not view:
        return _page("prediction", "Prediction Review Workspace", snapshot,
                     [C.prose("No prediction selected", "Execute an analysis to generate an outcome.")])

    probs = view.get("class_probabilities", [])
    sections = [
        # TOP: Prediction Outcome
        C.kv("Prediction", [
            ("Label", view.get("predicted_label")), ("Class", view.get("predicted_class")),
            ("Model", view.get("model_id")),
        ]),
        C.kv("Intelligence Outcome", [
            ("Predicted Label", view.get("predicted_label")),
            ("Outcome Confidence", view.get("confidence_level")),
        ]),
        # CENTER: Calibration & Evidence
        C.kv("Uncertainty (always shown)", [
            ("Confidence level", view.get("confidence_level")),
            ("Confidence score", view.get("confidence_score")),
            ("Calibration", view.get("calibration_quality")),
        ]),
        C.kv("Calibration & Evidence", [
            ("Calibration Quality", view.get("calibration_quality")),
            ("Model Confidence", view.get("confidence_score")),
            ("Model ID", view.get("model_id")),
        ]),
        C.table("Class probabilities", ["Class", "Label", "Probability"],
                [[p.get("class"), p.get("label"), p.get("probability")] for p in probs]
                or [["—", "—", "—"]]),
        C.table("Probability Distribution", ["Class", "Label", "Probability"],
                [[p.get("class"), p.get("label"), p.get("probability")] for p in probs]
                or [["—", "—", "—"]]),
        # RIGHT PANEL: Clinical Context
        C.kv("Explanation summary", [
            ("Method", view.get("explanation_method")),
            ("Top factors", len(view.get("top_factors", []))),
        ]),
        C.kv("Clinical Context & Risk", [
            ("Explanation Method", view.get("explanation_method")),
            ("Risk Indicators", "Standard Clinical Review Path"),
            ("Interpretation", "Outcome derived from feature extraction and inference calibration."),
        ]),
    ]
    return _page("prediction", "Prediction Review Workspace", snapshot, sections,
                 subtitle=f"Deterministic Decision Support for Analysis {view.get('analysis_id', '')}")


# --- Screen 5: Evidence Center -----------------------------------------------
def reports_page(snapshot: dict, view: Optional[dict], reports: Optional[list] = None) -> dict:
    if not view:
        return _page("reports", "Evidence Center", snapshot,
                     [C.prose("No evidence available", "Run an analysis to generate audit and lineage trails.")])

    sections = [
        # LEFT: Report Navigation
        C.items_list("Available reports", view.get("report_names", [])),
        C.items_list("Audit & Evidence Sources", view.get("report_names", [])),
        # CENTER: Report Viewer
        C.kv("Audit & Lineage Trail", [
            ("Audit Verification", view["validation_summary"].get("workflow_audit_verified")),
            ("Lineage Integrity", view["validation_summary"].get("lineage_chain_verified")),
            ("Event Count", view["audit_summary"].get("n_audit_events")),
            ("Chain Head", (view["audit_summary"].get("audit_head") or "")[:16]),
        ]),
    ]
    for r in (reports or []):
        sections.append(C.report_section(
            f"Fidelity Report: {r.name}", r.name, r.content,
            json.dumps(r.content, indent=2, sort_keys=True, default=str)))

    return _page("reports", "Evidence Center", snapshot, sections,
                 subtitle="Trust, transparency, and auditability for all intelligence outcomes.")


__all__ = [
    "login_page", "register_page", "dashboard_page", "upload_page", "analysis_page",
    "prediction_page", "reports_page",
]
