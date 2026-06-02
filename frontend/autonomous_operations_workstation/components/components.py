"""Reusable presentation components (V4-P8) — stdlib only (NR-8).

Tiny builders that turn registered-artifact data into :class:`Section` /
:class:`Visualization` view-models. They add no truth; they only shape data already
present in the snapshot for display.
"""

from __future__ import annotations

from ..schemas import Section, Visualization


def kv_panel(title: str, data: dict) -> Section:
    return Section(kind="kv", title=title, data=dict(data))


def text_panel(title: str, text: str) -> Section:
    return Section(kind="text", title=title, data={"text": text})


def table(title: str, columns: list, rows: list) -> Section:
    return Section(kind="table", title=title,
                   data={"columns": list(columns), "rows": [list(r) for r in rows]})


def badges(title: str, items: list) -> Section:
    """``items`` is a list of (label, ok_bool) or (label, value) pairs."""
    return Section(kind="badges", title=title,
                   data={"badges": [{"label": lbl, "value": val} for lbl, val in items]})


def bar_chart(title: str, labels: list, values: list) -> Visualization:
    return Visualization(type="bar", title=title,
                         spec={"labels": list(labels), "values": list(values)})


def table_viz(title: str, columns: list, rows: list) -> Visualization:
    return Visualization(type="table", title=title,
                         spec={"columns": list(columns), "rows": [list(r) for r in rows]})


def timeline(title: str, events: list) -> Visualization:
    return Visualization(type="timeline", title=title, spec={"events": list(events)})


def graph(title: str, nodes: list, edges: list) -> Visualization:
    return Visualization(type="graph", title=title,
                         spec={"nodes": list(nodes), "edges": list(edges)})
