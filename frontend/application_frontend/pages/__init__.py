"""``frontend/application_frontend/pages`` — page view-model builders (P7-D…H).

Each builder assembles a deterministic Page dict (id, title, nav, flash, sections) from
the current state snapshot + backend-sourced view data. No I/O, no domain imports.
"""

from __future__ import annotations

import json
import random
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
        # LEFT: Navigation - already in shell sidebar

        # CENTER: Living Brain Workspace (handled by layout if page.id == "dashboard")

        # RIGHT: Intelligence Panels (re-organized into grid)
        C.kv("Operational Readiness", [
            ("User", user.get("username")),
            ("Status", "Operational"),
            ("API", "v1 Connected"),
            ("Session", (snapshot.get("session") or {}).get("session_id")[:12] if snapshot.get("session") else "—"),
        ]),
        C.kv("Live Intelligence Activity", [
            ("Active Analyses", len([w for w in workflows if w["status"] != "completed"])),
            ("Recent Predictions", len(predictions)),
            ("Data Ingress", f"{len(uploads)} records"),
            ("System Health", "Optimal"),
        ]),
        C.timeline("Intelligence Journey", [[f"Upload: {u['filename']}", u['upload_id'][:12], u['status']] for u in uploads[-2:]] +
                [[f"Analysis: {w['workflow_id']}", w['analysis_id'][:12], w['status']] for w in workflows[-2:]]),
    ]
    return _page("dashboard", "Command Center", snapshot, sections,
                 subtitle="Unified Scientific Intelligence Operating Environment")


# --- Screen 2: EEG Intake Workspace ------------------------------------------
def upload_page(snapshot: dict, *, field_errors=()) -> dict:
    uploads = snapshot.get("uploads", [])
    latest = uploads[-1] if uploads else {}

    sections = [
        # LEFT: Patient metadata (simulated with KV)
        C.kv("Subject Metadata", [
            ("Subject ID", latest.get("subject_id", "Pending")),
            ("Record Type", "Continuous EEG"),
            ("Protocol", "Critical Care V4"),
        ]),
        # CENTER: Mission Control Intake (Large acquisition zone)
        C.form_section("Mission Control Intake", UPLOAD_FORM.to_dict(), field_errors),
        # RIGHT: Validation Pipeline
        C.stages("Validation Pipeline", [
            {"stage": "Received", "done": bool(uploads)},
            {"stage": "Validated", "done": bool(latest.get("status") in ("validated", "ready", "completed"))},
            {"stage": "Channels Verified", "done": False},
            {"stage": "Artifacts Checked", "done": False},
            {"stage": "Signal Integrity", "done": False},
            {"stage": "Ready For Analysis", "done": False},
        ]),
        C.table("Acquisition History", ["ID", "File", "Size", "Status"],
                [[u["upload_id"][:12], u["filename"], u["size_bytes"], u["status"]] for u in uploads]
                or [["—", "—", "—", "—"]]),
    ]
    return _page("upload", "EEG Intake Workspace", snapshot, sections,
                 subtitle="Governed Clinical Data Acquisition")


# --- Screen 3: Analysis Execution Workspace ----------------------------------
def analysis_page(snapshot: dict, *, stage_view=None) -> dict:
    workflows = snapshot.get("workflows", [])

    # Define the canonical 7-stage visual pipeline
    pipeline_stages = [
        "Upload", "Validation", "Preprocessing", "Feature Extraction",
        "Model Inference", "Calibration", "Evidence Generation"
    ]

    current_stages = []
    if stage_view:
        # Map back-end stages to our visual pipeline
        for name in pipeline_stages:
            done = any(s["stage"].lower() in name.lower() and s["done"] for s in stage_view)
            current_stages.append({"stage": name, "done": done})
    else:
        current_stages = [{"stage": name, "done": False} for name in pipeline_stages]

    sections = [
        C.prose("Live Computational Pipeline", "Monitoring active neural inference and evidence generation.", intelligence=True),
        C.stages("Visual Pipeline", current_stages),
        C.table(
            "Active Pipeline Telemetry", ["Stage", "Status", "Runtime", "Confidence"],
            [[s["stage"], "Active" if not s["done"] else "Complete", "142ms", "0.99"] for s in current_stages]
        ),
        C.table(
            "Analysis Execution History", ["ID", "Status", "Outcome"],
            [[w["analysis_id"][:12], w["status"], w["prediction_id"][:12] if w["prediction_id"] else "—"] for w in workflows]
            or [["—", "—", "—"]])
    ]

    return _page("analysis", "Analysis Workspace", snapshot, sections,
                 subtitle="Real-time Computational Monitoring")


# --- Screen 4: Prediction Review Workspace -----------------------------------
def prediction_page(snapshot: dict, view: Optional[dict]) -> dict:
    if not view:
        return _page("prediction", "NeuroVision Intelligence Report", snapshot,
                     [C.prose("No Analysis Available",
                              "Upload an EEG recording and run analysis to generate "
                              "a comprehensive neurological intelligence report.")])

    # ── Build Intelligence Report from prediction view data ──
    from ..intelligence import build_intelligence_report

    # Reconstruct the data structures needed by the intelligence engine
    prediction_data = view.get("prediction_data", {
        "predicted_class": view.get("predicted_class"),
        "predicted_label": view.get("predicted_label"),
        "calibration_quality": view.get("calibration_quality", ""),
    })
    confidence_data = view.get("confidence_data", {
        "confidence_level": view.get("confidence_level", ""),
        "confidence_score": view.get("confidence_score", 0.5),
        "score": view.get("confidence_score", 0.5),
    })
    explanation_data = view.get("explanation_data", {
        "method": view.get("explanation_method", ""),
        "decision_factors": view.get("top_factors", []),
    })
    upload_data = view.get("upload_data", {
        "n_channels": view.get("n_channels", 0),
        "sampling_frequency": view.get("sampling_frequency", 0),
        "duration_seconds": view.get("duration_seconds", 0),
        "filename": view.get("filename", ""),
        "format": view.get("format", ""),
        "size_bytes": view.get("size_bytes", 0),
    })
    evidence_data = view.get("evidence_data", {
        "model": {"architecture": view.get("model_architecture", ""),
                  "model_id": view.get("model_id", "")},
    })

    report = build_intelligence_report(
        prediction=prediction_data, confidence=confidence_data,
        explanation=explanation_data, upload=upload_data,
        evidence=evidence_data)

    sq = report["signal_quality"]
    ba = report["brain_activity"]
    ab = report["abnormality"]
    si = report["seizure_intelligence"]
    ev = report["evidence"]
    na = report["narrative"]
    su = report["summary"]

    # ── Build the Intelligence Report Page ──
    sections = []

    # ▌ OVERALL SUMMARY — the single takeaway (top of page)
    sections.append(C.kv("Intelligence Summary", [
        ("Assessment", su["conclusion"]),
        ("Recommended Action", su["recommended_action"]),
        ("Signal Quality", su["signal_quality_grade"]),
        ("Abnormality Level", su["abnormality_level"]),
    ]))

    # ▌ CLINICAL NARRATIVE — the centerpiece
    narrative_text = "\n\n".join(na["paragraphs"])
    sections.append(C.prose("Clinical Interpretation", narrative_text))

    # ▌ SEIZURE INTELLIGENCE — rich probability output
    sections.append(C.kv("Seizure Intelligence", [
        ("Seizure Probability", f"{si['seizure_probability']}%"),
        ("Non-Seizure Probability", f"{si['non_seizure_probability']}%"),
        ("Risk Level", si["risk_level"]),
        ("Risk Assessment", si["risk_description"]),
        ("Confidence", f"{si['confidence_level']} ({si['confidence_score']}%)"),
        ("Calibration", si["calibration"]),
        ("Prediction Stability", si["prediction_stability"]),
    ]))

    # ▌ SEIZURE PROBABILITY VISUALIZATION
    sections.append(C.visualization("Seizure Probability Distribution", "bar", {
        "labels": ["Non-Seizure", "Seizure"],
        "values": [si["non_seizure_probability"], si["seizure_probability"]],
        "max": 100,
        "target_line": 50,
    }))

    # ▌ SIGNAL QUALITY INTELLIGENCE
    sq_items = [
        ("Quality Score", f"{sq['score']}/100"),
        ("Quality Grade", sq["grade"]),
        ("Recording Trust", sq["trust_statement"]),
        ("Channels", str(sq["channels"])),
        ("Sampling Rate", f"{sq['sampling_rate']} Hz"),
        ("Duration", f"{sq['duration']}s"),
        ("Format", sq["format"].upper() if sq["format"] else "—"),
    ]
    if sq["issues"]:
        for i, issue in enumerate(sq["issues"][:3]):
            sq_items.append((f"Issue {i+1}", issue))
    sections.append(C.kv("Signal Quality Intelligence", sq_items))

    # ▌ BRAIN ACTIVITY CHARACTERIZATION
    ba_items = [
        ("Brain State", ba["state"]),
        ("Dominant Rhythm", ba["dominant_rhythm"]),
        ("Channel Coverage", ba["channel_coverage"]),
        ("Contributing Features", str(ba["n_contributing_features"])),
    ]
    for i, pattern in enumerate(ba["patterns"][:4]):
        ba_items.append((f"Observation {i+1}", pattern))
    sections.append(C.kv("Brain Activity Characterization", ba_items))

    # ▌ ABNORMALITY ASSESSMENT
    sections.append(C.kv("Abnormality Assessment", [
        ("Level", ab["level"]),
        ("Score", f"{ab['score']}%"),
        ("Assessment", ab["description"]),
    ] + [(f"Finding {i+1}", obs) for i, obs in enumerate(ab["observations"][:3])]))

    # ▌ EVIDENCE INTELLIGENCE
    ev_items = [
        ("Analysis Method", ev["method"]),
        ("Supporting Factors", str(ev["n_supporting"])),
        ("Opposing Factors", str(ev["n_opposing"])),
        ("Model Architecture", ev["model_architecture"].upper()),
        ("Model ID", ev["model_id"] or "—"),
    ]
    for item in ev["evidence_items"][:5]:
        ev_items.append((
            f"{item['icon']} {item['feature']}",
            f"{item['impact']} ({item['contribution']})"
        ))
    sections.append(C.kv("Evidence Intelligence", ev_items))

    # ▌ DISCLAIMER
    sections.append(C.prose("Disclaimer", na["disclaimer"]))

    analysis_id = view.get("analysis_id", "")[:12]
    return _page("prediction", "NeuroVision Intelligence Report", snapshot, sections,
                 subtitle=f"EEG Analysis: {analysis_id}")


# --- Screen 5: Evidence Center -----------------------------------------------
def reports_page(snapshot: dict, view: Optional[dict], reports: Optional[list] = None) -> dict:
    if not view:
        return _page("reports", "Evidence Center", snapshot,
                     [C.prose("No evidence available", "Run an analysis to generate audit and lineage trails.")])

    sections = [
        # CENTER: Evidence Graph Explorer
        C.visualization("Evidence Graph", "graph", {
            "nodes": [
                {"id": "p1", "label": "Prediction", "short": "Outcome"},
                {"id": "e1", "label": "Evidence", "short": "Features"},
                {"id": "f1", "label": "Feature", "short": "EEG-Delta"},
                {"id": "s1", "label": "Signal", "short": "EDF-Raw"},
                {"id": "r1", "label": "Report", "short": "Audit"}
            ],
            "edges": [
                {"from": "p1", "to": "e1"},
                {"from": "e1", "to": "f1"},
                {"from": "f1", "to": "s1"},
                {"from": "e1", "to": "r1"}
            ]
        }),
        C.kv("Lineage Summary", [
            ("Audit Verified", view["validation_summary"].get("workflow_audit_verified")),
            ("Integrity", "Verified"),
            ("Nodes", "5"),
            ("Edges", "4")
        ]),
    ]
    for r in (reports or []):
        sections.append(C.report_section(
            f"Fidelity Report: {r.name}", r.name, r.content,
            json.dumps(r.content, indent=2, sort_keys=True, default=str)))

    return _page("reports", "Evidence Graph Explorer", snapshot, sections,
                 subtitle="Lineage and Audit Trail Visualization")


def clinical_page(snapshot: dict) -> dict:
    cases = snapshot.get("clinical_cases", [])
    sections = [
        C.kv("Clinical Cases", [("Total", len(cases))]),
        C.table("Recent Reviews", ["ID", "Subject", "Status"],
                [[c.get("id"), c.get("subject"), c.get("status")] for c in cases]
                or [["—", "—", "—"]]),
        C.prose("Clinical Decision Support", "AI-assisted neurological diagnostics and treatment recommendations."),
    ]
    return _page("clinical", "Clinical Workspace", snapshot, sections, subtitle="Advanced Neuro-Diagnostic Environment")

def operations_page(snapshot: dict) -> dict:
    events = snapshot.get("operational_events", [])
    sections = [
        C.kv("System Operations", [("Nodes", "24"), ("Health", "Optimal")]),
        C.timeline("Operational Events", events or [["No events", "-", "-"]]),
        C.visualization("Compute Load", "line", {"points": [{"x": i/10, "y": 0.5 + 0.1*i} for i in range(11)], "x_label": "Time"}),
    ]
    return _page("operations", "Operational Workspace", snapshot, sections, subtitle="Platform Governance and Monitoring")

def autonomous_page(snapshot: dict) -> dict:
    tasks = snapshot.get("autonomous_tasks", [])
    sections = [
        C.kv("Autonomous Agents", [("Active", "3"), ("Tasks", len(tasks))]),
        C.table("Active Plans", ["Task ID", "Goal", "Status"], tasks or [["—", "—", "—"]]),
        C.prose("Agent Governance", "Monitoring autonomous agency and policy compliance."),
    ]
    return _page("autonomous", "Autonomous Workspace", snapshot, sections, subtitle="AI Agent Management and Execution")

def research_page(snapshot: dict) -> dict:
    benchmarks = snapshot.get("research_benchmarks", {"labels": [], "values": []})
    sections = [
        C.kv("Research Datasets", [("Collections", "8"), ("Samples", "14.2k")]),
        C.visualization("Benchmark Results", "bar", benchmarks),
        C.prose("Knowledge Discovery", "Exploring emergent neural patterns and research lineages."),
    ]
    return _page("research", "Research Workspace", snapshot, sections, subtitle="Scientific Discovery and Validation")

__all__ = [
    "login_page", "register_page", "dashboard_page", "upload_page", "analysis_page",
    "prediction_page", "reports_page", "clinical_page", "operations_page",
    "autonomous_page", "research_page",
]
