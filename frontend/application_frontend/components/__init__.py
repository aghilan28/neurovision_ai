"""``frontend/application_frontend/components`` — reusable view-model fragments.

Pure builders that return plain section dicts (the layout renderer turns them into
deterministic static HTML). No state, no I/O, no domain imports.
"""

from __future__ import annotations

# The primary navigation areas (id, label, requires authentication).
NAV_AREAS = (
    ("dashboard", "Command Center", True),
    ("upload", "EEG Intake", True),
    ("analysis", "Analysis", True),
    ("prediction", "Predictions", True),
    ("reports", "Evidence Center", True),
    ("clinical", "Clinical Workspace", True),
    ("operations", "Operations Workspace", True),
    ("autonomous", "Autonomous Workspace", True),
    ("research", "Research Workspace", True),
)


def nav(state_snapshot: dict) -> list:
    """Build the nav items appropriate to the current auth state."""
    authed = state_snapshot.get("authenticated")
    current = state_snapshot.get("current_page")
    items = []
    if authed:
        for area_id, label, _ in NAV_AREAS:
            items.append({"id": area_id, "label": label, "active": area_id == current})
        items.append({"id": "logout", "label": "Log out", "active": False})
    else:
        items.append({"id": "login", "label": "Log in", "active": current == "login"})
        items.append({"id": "register", "label": "Register", "active": current == "register"})
    return items


def alert(level: str, message: str) -> dict:
    return {"type": "alert", "level": level or "info", "message": message or ""}


def kv(heading: str, rows) -> dict:
    return {"type": "kv", "heading": heading,
            "rows": [[str(k), "" if v is None else str(v)] for k, v in rows]}


def table(heading: str, columns, rows) -> dict:
    return {"type": "table", "heading": heading, "columns": list(columns),
            "rows": [["" if c is None else str(c) for c in row] for row in rows]}


def timeline(heading: str, events) -> dict:
    """Build a timeline section (item, subtext, status)."""
    return {"type": "timeline_records", "heading": heading,
            "items": [{"label": str(e[0]), "text": str(e[1]), "status": str(e[2])} for e in events]}


def form_section(heading: str, form: dict, field_errors=()) -> dict:
    return {"type": "form", "heading": heading, "form": form,
            "field_errors": [{"field": f, "message": m} for f, m in (field_errors or ())]}


def stages(heading: str, stage_list) -> dict:
    return {"type": "stages", "heading": heading,
            "stages": [{"stage": s["stage"], "done": bool(s["done"])} for s in stage_list]}


def items_list(heading: str, items) -> dict:
    return {"type": "list", "heading": heading, "items": [str(i) for i in items]}


def report_section(heading: str, name: str, content: dict, pretty_json: str) -> dict:
    return {"type": "report", "heading": heading, "name": name, "json": pretty_json}


def prose(heading: str, text: str, intelligence: bool = False) -> dict:
    return {"type": "prose", "heading": heading, "text": text, "intelligence": intelligence}


def visualization(title: str, typ: str, spec: dict) -> dict:
    return {"type": "visualization", "title": title, "visualization_type": typ, "spec": spec}


__all__ = [
    "NAV_AREAS", "nav", "alert", "kv", "table", "form_section", "stages", "items_list",
    "report_section", "prose", "visualization",
]
