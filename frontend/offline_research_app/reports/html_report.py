"""Deterministic static-HTML renderer for the research application.

Produces a single self-contained HTML page (inline CSS + inline SVG, CSS-only
tabs, no JavaScript, no external assets) so it works fully offline and is
byte-deterministic for a given view-model (no timestamps). Renderer-only: it draws
exactly what the registered artifacts contain.
"""

from __future__ import annotations

import html
import json
import os

from ..schemas import AppView
from ..state import AppState
from ..pages import build_app_view
from ..version import OFFLINE_RESEARCH_APP_VERSION

_CSS = """
:root{--bg:#0f1419;--panel:#1a2129;--ink:#e6edf3;--muted:#9aa7b2;--ok:#2ea043;--fail:#d1242f;--accent:#3b82f6;--line:#30363d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:16px 24px;border-bottom:1px solid var(--line)}
h1{font-size:18px;margin:0}.sub{color:var(--muted);font-size:12px}
.tabs{display:flex;flex-wrap:wrap;gap:4px;padding:12px 24px 0}
.tabs label{padding:8px 14px;background:var(--panel);border:1px solid var(--line);border-bottom:none;border-radius:6px 6px 0 0;cursor:pointer;color:var(--muted)}
input.tab{position:absolute;left:-9999px}
.panel{display:none;padding:20px 24px;border-top:1px solid var(--line)}
section.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:0 0 16px}
section.card h3{margin:0 0 10px;font-size:14px;color:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
.kv{display:grid;grid-template-columns:240px 1fr;gap:4px 12px}
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
    vmax = spec.get("max") or (max(values) if max(values) > 0 else 1.0)
    W, H, pad, bw = 620, 220, 30, max(8, int(560 / max(1, len(values)) * 0.6))
    gap = (560 - bw * len(values)) / max(1, len(values))
    bars = []
    for i, (lab, val) in enumerate(zip(labels, values)):
        h = (val / vmax) * (H - 2 * pad) if vmax else 0
        x = pad + i * (bw + gap)
        y = H - pad - h
        bars.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw:.1f}' height='{h:.1f}' fill='#3b82f6'/>")
        bars.append(f"<text x='{x + bw/2:.1f}' y='{H-pad+12:.1f}' fill='#9aa7b2' font-size='9' text-anchor='middle'>{_esc(lab)[:8]}</text>")
        bars.append(f"<text x='{x + bw/2:.1f}' y='{y-3:.1f}' fill='#e6edf3' font-size='9' text-anchor='middle'>{val:.3g}</text>")
    target = spec.get("target_line")
    if isinstance(target, (int, float)) and vmax:
        ty = H - pad - (target / vmax) * (H - 2 * pad)
        bars.append(f"<line x1='{pad}' y1='{ty:.1f}' x2='{W-pad}' y2='{ty:.1f}' stroke='#d1242f' stroke-dasharray='4'/>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(bars)}</svg>"


def _line_svg(spec: dict) -> str:
    pts = spec.get("points", [])
    W, H, pad = 320, 320, 36
    inner = H - 2 * pad
    body = [f"<rect x='{pad}' y='{pad}' width='{inner}' height='{inner}' fill='none' stroke='#30363d'/>"]
    if spec.get("diagonal"):
        body.append(f"<line x1='{pad}' y1='{H-pad}' x2='{W-pad}' y2='{pad}' stroke='#9aa7b2' stroke-dasharray='3'/>")
    coords = []
    for p in pts:
        x = p.get("x"); y = p.get("y")
        if x is None or y is None:
            continue
        px = pad + float(x) * inner
        py = (H - pad) - float(y) * inner
        coords.append((px, py))
        body.append(f"<circle cx='{px:.1f}' cy='{py:.1f}' r='3' fill='#3b82f6'/>")
    if len(coords) > 1:
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        body.append(f"<polyline points='{path}' fill='none' stroke='#3b82f6' stroke-width='1.5'/>")
    body.append(f"<text x='{W/2:.0f}' y='{H-8}' fill='#9aa7b2' font-size='10' text-anchor='middle'>{_esc(spec.get('x_label','x'))}</text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(body)}</svg>"


def _graph_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    W = 620
    row_h = 70
    H = max(120, row_h * max(1, len(nodes)) + 20)
    pos = {}
    for i, n in enumerate(nodes):
        x = 80 + (i % 3) * 200
        y = 40 + i * (row_h)
        pos[n["id"]] = (x, y)
    body = []
    for e in edges:
        if e["from"] in pos and e["to"] in pos:
            x1, y1 = pos[e["from"]]; x2, y2 = pos[e["to"]]
            body.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#30363d'/>")
    for n in nodes:
        x, y = pos[n["id"]]
        body.append(f"<circle cx='{x}' cy='{y}' r='10' fill='#3b82f6'/>")
        body.append(f"<text x='{x+16}' y='{y+4}' fill='#e6edf3' font-size='11'>{_esc(n.get('label'))} <tspan fill='#9aa7b2'>{_esc(n.get('short',''))}</tspan></text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(body)}</svg>"


def _layout_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    W, H = 360, 320
    body = []
    for n in nodes:
        x = float(n.get("x", 0.5)) * W
        y = float(n.get("y", 0.5)) * H
        color = "#3b82f6" if n.get("group") == "left" else "#22c55e"
        body.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='9' fill='{color}'/>")
        body.append(f"<text x='{x:.1f}' y='{y-12:.1f}' fill='#e6edf3' font-size='10' text-anchor='middle'>{_esc(n.get('label'))}</text>")
    return f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>{''.join(body)}</svg>"


def _viz_html(viz: dict) -> str:
    t = viz["type"]
    spec = viz["spec"]
    if t == "bar":
        inner = _bar_svg(spec)
    elif t == "line":
        inner = _line_svg(spec)
    elif t == "graph":
        inner = _graph_svg(spec)
    elif t == "layout":
        inner = _layout_svg(spec)
    elif t == "table":
        rows = spec.get("rows", [])
        inner = "<table>" + "".join(
            "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>"
    else:
        inner = "<p class='sub'>(unsupported viz)</p>"
    return f"<section class='card'><h3>{_esc(viz['title'])}</h3>{inner}</section>"


def _section_html(sec: dict) -> str:
    kind = sec["kind"]
    data = sec["data"]
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


def render_app_html(app_view: AppView) -> str:
    """Render the application view-model to a deterministic static HTML string."""
    view = app_view.to_dict() if isinstance(app_view, AppView) else app_view
    pages = view["pages"]
    meta = view["meta"]
    val = view["validation"]

    tabs = []
    panels = []
    for i, page in enumerate(pages):
        checked = " checked" if i == 0 else ""
        pid = _esc(page["id"])
        tabs.append(f"<input class='tab' type='radio' name='tabs' id='tab-{pid}'{checked}>"
                    f"<label for='tab-{pid}'>{_esc(page['title'])}</label>")
        body = "".join(_section_html(s) for s in page["sections"])
        body += "".join(_viz_html(v) for v in page["visualizations"])
        panels.append(f"<div class='panel' id='panel-{pid}'>{body}</div>")

    # CSS to reveal the panel whose radio is checked (CSS-only tabs)
    reveal = "".join(
        f"#tab-{_esc(p['id'])}:checked ~ #panel-{_esc(p['id'])}{{display:block}}" for p in pages)
    val_badge = "pass" if val.get("ok") else "fail"

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>NeuroVision AI — Offline Research App</title><style>{_CSS}{reveal}</style></head><body>"
        "<header><h1>NeuroVision AI — Offline Research Application</h1>"
        f"<div class='sub mono'>{OFFLINE_RESEARCH_APP_VERSION} · inference {_esc(meta.get('inference_id'))} · "
        f"lineage {_esc(meta.get('lineage_id'))} · "
        f"app validation: <span class='badge {val_badge}'>{'OK' if val.get('ok') else 'FAILED'}</span></div>"
        "<div class='sub'>Presentation only — every value originates from registered artifacts.</div></header>"
        f"<div class='tabs'>{''.join(tabs)}{''.join(panels)}</div>"
        "</body></html>"
    )


def render_from_run_dir(run_dir: str) -> str:
    return render_app_html(build_app_view(AppState.load(run_dir)))


def write_app_html(run_dir: str, path: str | None = None) -> str:
    """Render and write the static HTML report; returns the output path."""
    html_str = render_from_run_dir(run_dir)
    path = path or os.path.join(run_dir, "research_app.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return path
