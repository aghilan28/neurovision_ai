"""Deterministic static-HTML renderer for the Operational Workstation (V3-P7).

Produces a single self-contained HTML page (inline CSS + inline SVG, CSS-only nav,
no JavaScript, no external assets) so the unified operational environment works
fully offline and is byte-deterministic for a given view-model (no timestamps).
Renderer-only: it draws exactly what the registered artifacts contain.
"""

from __future__ import annotations

import html
import json
import os

from ..schemas import WorkstationView
from ..state import WorkstationState
from ..application import build_workstation_view
from ..version import OPERATIONAL_WORKSTATION_VERSION

_CSS = """
:root{--bg:#0f1419;--panel:#1a2129;--ink:#e6edf3;--muted:#9aa7b2;--ok:#2ea043;--fail:#d1242f;--accent:#3b82f6;--line:#30363d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:16px 24px;border-bottom:1px solid var(--line)}
h1{font-size:18px;margin:0}.sub{color:var(--muted);font-size:12px}
.nav{display:flex;flex-wrap:wrap;gap:4px;padding:12px 24px 0}
.nav label{padding:8px 14px;background:var(--panel);border:1px solid var(--line);border-bottom:none;border-radius:6px 6px 0 0;cursor:pointer;color:var(--muted)}
input.nav{position:absolute;left:-9999px}
.area{display:none;padding:18px 24px;border-top:1px solid var(--line)}
.pagebar{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}
.pagebar .pg{padding:4px 10px;border:1px solid var(--line);border-radius:12px;color:var(--muted);font-size:12px;background:#0b0f14}
section.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:0 0 16px}
section.card h3{margin:0 0 10px;font-size:14px;color:var(--ink)}
h2.page{font-size:15px;margin:18px 0 10px;color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
.kv{display:grid;grid-template-columns:260px 1fr;gap:4px 12px}
.kv .k{color:var(--muted)}.kv .v{font-family:ui-monospace,Menlo,monospace;word-break:break-word}
.badge{display:inline-block;padding:3px 9px;border-radius:12px;font-size:12px;margin:2px}
.badge.pass{background:rgba(46,160,67,.15);color:var(--ok);border:1px solid var(--ok)}
.badge.fail{background:rgba(209,36,47,.15);color:var(--fail);border:1px solid var(--fail)}
.badge.neutral{background:rgba(155,167,178,.12);color:var(--muted);border:1px solid var(--line)}
svg{background:#0b0f14;border:1px solid var(--line);border-radius:6px}
.mono{font-family:ui-monospace,Menlo,monospace}
"""


def _esc(v) -> str:
    if isinstance(v, (dict, list)):
        return html.escape(json.dumps(v, sort_keys=True, separators=(",", ":")))
    return html.escape("" if v is None else str(v))


def _bar_svg(spec: dict) -> str:
    labels = spec.get("labels", [])
    values = [float(v) for v in spec.get("values", [])]
    if not values:
        return "<p class='sub'>(no data)</p>"
    vmin = spec.get("min", 0.0)
    vmax = spec.get("max") or (max(values) if max(values) > 0 else 1.0)
    span = (vmax - vmin) or 1.0
    W, H, pad = 620, 220, 30
    bw = max(8, int(560 / max(1, len(values)) * 0.6))
    gap = (560 - bw * len(values)) / max(1, len(values))
    bars = []
    for i, (lab, val) in enumerate(zip(labels, values)):
        h = ((val - vmin) / span) * (H - 2 * pad)
        x = pad + i * (bw + gap)
        y = H - pad - h
        bars.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw:.1f}' height='{max(0, h):.1f}' fill='#3b82f6'/>")
        bars.append(f"<text x='{x + bw/2:.1f}' y='{H-pad+12:.1f}' fill='#9aa7b2' font-size='9' text-anchor='middle'>{_esc(lab)[:10]}</text>")
        bars.append(f"<text x='{x + bw/2:.1f}' y='{y-3:.1f}' fill='#e6edf3' font-size='9' text-anchor='middle'>{val:.3g}</text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(bars)}</svg>"



def _graph_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    W = 640
    row_h = 52
    H = max(120, row_h * max(1, len(nodes)) + 20)
    pos = {}
    for i, n in enumerate(nodes):
        x = 90 + (i % 3) * 210
        y = 36 + i * row_h
        pos[n["id"]] = (x, y)
    body = []
    for e in edges:
        if e["from"] in pos and e["to"] in pos:
            x1, y1 = pos[e["from"]]
            x2, y2 = pos[e["to"]]
            body.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#30363d'/>")
    for n in nodes:
        x, y = pos[n["id"]]
        body.append(f"<circle cx='{x}' cy='{y}' r='9' fill='#3b82f6'/>")
        body.append(f"<text x='{x+15}' y='{y+4}' fill='#e6edf3' font-size='11'>{_esc(n.get('label'))} "
                    f"<tspan fill='#9aa7b2'>{_esc(n.get('short',''))}</tspan></text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(body)}</svg>"


def _timeline_svg(spec: dict) -> str:
    events = spec.get("events", [])
    W, H, pad = 640, 90, 30
    n = len(events)
    if n == 0:
        return "<p class='sub'>(no events)</p>"
    step = (W - 2 * pad) / max(1, n - 1)
    body = [f"<line x1='{pad}' y1='{H/2}' x2='{W-pad}' y2='{H/2}' stroke='#30363d'/>"]
    for i, e in enumerate(events[:60]):
        x = pad + i * step
        body.append(f"<circle cx='{x:.1f}' cy='{H/2}' r='4' fill='#3b82f6'/>")
        if i % 4 == 0:
            body.append(f"<text x='{x:.1f}' y='{H/2-8:.1f}' fill='#9aa7b2' font-size='8' text-anchor='middle'>{_esc(e.get('seq'))}</text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(body)}</svg>"


def _viz_html(viz: dict) -> str:
    t, spec = viz["type"], viz["spec"]
    if t == "bar":
        inner = _bar_svg(spec)
    elif t == "graph":
        inner = _graph_svg(spec)
    elif t == "timeline":
        inner = _timeline_svg(spec)
    elif t == "table":
        head = "".join(f"<th>{_esc(h)}</th>" for h in spec.get("headers", []))
        inner = "<table>" + (f"<tr>{head}</tr>" if head else "") + "".join(
            "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>"
            for r in spec.get("rows", [])) + "</table>"
    else:
        inner = "<p class='sub'>(unsupported viz)</p>"
    return f"<section class='card'><h3>{_esc(viz['title'])}</h3>{inner}</section>"


def _section_html(sec: dict) -> str:
    kind, data = sec["kind"], sec["data"]
    if kind == "kv":
        rows = "".join(f"<div class='k'>{_esc(k)}</div><div class='v'>{_esc(v)}</div>"
                       for k, v in data.get("pairs", {}).items())
        body = f"<div class='kv'>{rows}</div>"
    elif kind == "table":
        head = "".join(f"<th>{_esc(h)}</th>" for h in data.get("headers", []))
        body_rows = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>"
                            for r in data.get("rows", []))
        body = f"<table><tr>{head}</tr>{body_rows}</table>"
    elif kind == "badges":
        parts = []
        for it in data.get("items", []):
            st = it["state"]
            cls = "pass" if st == "pass" else ("fail" if st == "fail" else "neutral")
            parts.append(f"<span class='badge {cls}'>{_esc(it['label'])}: {_esc(st)}</span>")
        body = "".join(parts)
    elif kind == "text":
        body = f"<p>{_esc(data.get('body',''))}</p>"
    else:
        body = "<p class='sub'>(unsupported section)</p>"
    return f"<section class='card'><h3>{_esc(sec['title'])}</h3>{body}</section>"


def _page_html(page: dict) -> str:
    body = f"<h2 class='page'>{_esc(page['title'])}</h2>"
    body += "".join(_section_html(s) for s in page["sections"])
    body += "".join(_viz_html(v) for v in page["visualizations"])
    return body



def render_workstation_html(view: WorkstationView) -> str:
    """Render the workstation view-model to a deterministic static HTML string."""
    v = view.to_dict() if isinstance(view, WorkstationView) else view
    areas, meta, val = v["areas"], v["meta"], v["validation"]

    nav, panels = [], []
    for i, area in enumerate(areas):
        checked = " checked" if i == 0 else ""
        aid = _esc(area["id"])
        nav.append(f"<input class='nav' type='radio' name='nav' id='nav-{aid}'{checked}>"
                   f"<label for='nav-{aid}'>{_esc(area['title'])}</label>")
        pagebar = "".join(f"<span class='pg'>{_esc(p['title'])}</span>" for p in area["pages"])
        pages_html = "".join(_page_html(p) for p in area["pages"])
        panels.append(f"<div class='area' id='area-{aid}'>"
                      f"<div class='pagebar'>{pagebar}</div>{pages_html}</div>")

    reveal = "".join(f"#nav-{_esc(a['id'])}:checked ~ #area-{_esc(a['id'])}{{display:block}}"
                     for a in areas)
    vb = "pass" if val.get("ok") else "fail"
    ctx = meta.get("context", {})
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>NeuroVision AI — Operational Intelligence Workstation</title>"
        f"<style>{_CSS}{reveal}</style></head><body>"
        "<header><h1>NeuroVision AI — Operational Intelligence Workstation</h1>"
        f"<div class='sub mono'>{OPERATIONAL_WORKSTATION_VERSION} · "
        f"events {_esc(meta.get('n_events'))} · workflows {_esc(meta.get('n_workflows'))} · "
        f"analytics {_esc(meta.get('n_analytics'))} · "
        f"recommendations {_esc(meta.get('n_recommendations'))} · "
        f"validation: <span class='badge {vb}'>{'OK' if val.get('ok') else 'FAILED'}</span></div>"
        f"<div class='sub'>context: event={_esc(ctx.get('current_event'))} "
        f"workflow={_esc(ctx.get('current_workflow'))} "
        f"recommendation={_esc(ctx.get('current_recommendation'))}</div>"
        "<div class='sub'>Presentation only — every value originates from registered artifacts.</div>"
        "</header>"
        f"<div class='nav'>{''.join(nav)}{''.join(panels)}</div>"
        "</body></html>"
    )


def render_from_snapshot_path(snapshot_path: str) -> str:
    return render_workstation_html(build_workstation_view(WorkstationState.load(snapshot_path)))


def write_workstation_html(snapshot_path: str, out_path: str | None = None) -> str:
    """Render and write the static HTML; returns the output path."""
    html_str = render_from_snapshot_path(snapshot_path)
    out_path = out_path or os.path.join(os.path.dirname(os.path.abspath(snapshot_path)),
                                        "operational_workstation.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return out_path
