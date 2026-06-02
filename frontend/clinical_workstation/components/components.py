"""Reusable presentation components (return ``Section`` view-models)."""

from __future__ import annotations

from ..schemas import Section


def kv_panel(title: str, mapping: dict) -> Section:
    """A key-value panel from a flat mapping."""
    rows = {str(k): mapping[k] for k in mapping}
    return Section(kind="kv", title=title, data={"pairs": rows})


def table(title: str, headers: list, rows: list) -> Section:
    """A table from explicit headers + row lists."""
    return Section(kind="table", title=title, data={"headers": list(headers),
                                                     "rows": [list(r) for r in rows]})


def badges(title: str, items: list) -> Section:
    """A row of status badges. ``items`` = list of (label, status_bool|str)."""
    norm = []
    for label, status in items:
        if isinstance(status, bool):
            state = "pass" if status else "fail"
        else:
            state = str(status)
        norm.append({"label": str(label), "state": state})
    return Section(kind="badges", title=title, data={"items": norm})


def text(title: str, body: str) -> Section:
    return Section(kind="text", title=title, data={"body": str(body)})


def metric_row(title: str, metrics: dict) -> Section:
    """A compact metric panel (numbers rounded for display)."""
    formatted = {}
    for k, v in metrics.items():
        formatted[str(k)] = (round(v, 4) if isinstance(v, (int, float)) and not isinstance(v, bool)
                             else v)
    return Section(kind="kv", title=title, data={"pairs": formatted})


def validation_badges(title: str, validation: dict) -> Section:
    """Render a serialized ValidationReport's checks as badges."""
    items = [(c["name"], c["passed"]) for c in validation.get("checks", [])]
    if not items:
        items = [("validated", bool(validation.get("ok", False)))]
    return badges(title, items)
