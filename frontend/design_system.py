"""NeuroVision presentation design system.

This module is intentionally presentation-only. It contains no backend calls, no
domain logic, and no state mutation. Existing controllers, gateways, state models,
validation, and artifact loaders remain the source of platform truth.
"""

from __future__ import annotations

import html
import json
from typing import Any


THEME_TOKENS = {
    "color": {
        "bg": "#12101B",
        "surface": "#181523",
        "panel": "#211D30",
        "panel_2": "#2A2440",
        "line": "rgba(168, 154, 232, 0.1)",
        "line_strong": "rgba(168, 154, 232, 0.2)",
        "text": "#E6EBF8",
        "muted": "#8A8895",
        "subtle": "#5D5B6A",
        "accent": "#A89AE8",
        "accent_2": "#4EE4B8",
        "warning": "#FFB84D",
        "danger": "#FF5577",
        "ok": "#A89AE8",
        "info": "#A89AE8",
        "intelligence": "#4EE4B8",
    },
    "typography": {
        "family": "'Inter', -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif",
        "mono": "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace",
    },
    "spacing": {"1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "20px", "6": "24px"},
    "radius": {"sm": "4px", "md": "8px", "lg": "12px"},
    "elevation": {"panel": "0 8px 32px rgba(0,0,0,.32)"},
    "animation": {"fast": "150ms ease", "standard": "250ms cubic-bezier(0.4, 0, 0.2, 1)"},
    "interaction": {"focus": "0 0 0 3px rgba(168, 154, 232, 0.2)"},
    "accessibility": {"min_contrast": "AA", "focus_visible": True},
    "status": {"ok": "ok", "warning": "warning", "danger": "danger", "info": "info"},
    "chart": {"bar": "#A89AE8", "line": "#4EE4B8", "grid": "rgba(168, 154, 232, 0.1)"},
    "workspace": {"sidebar_width": "280px", "top_bar_height": "72px", "content_max": "1600px"},
}


def esc(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return html.escape("" if value is None else str(value))


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, default=str)


def css(extra: str = "") -> str:
    c = THEME_TOKENS["color"]
    t = THEME_TOKENS["typography"]
    w = THEME_TOKENS["workspace"]
    return f"""
:root{{
  --bg:{c['bg']};--surface:{c['surface']};--panel:{c['panel']};--panel-2:{c['panel_2']};
  --line:{c['line']};--line-strong:{c['line_strong']};--text:{c['text']};--muted:{c['muted']};
  --subtle:{c['subtle']};--accent:{c['accent']};--accent-2:{c['accent_2']};
  --warning:{c['warning']};--danger:{c['danger']};--ok:{c['ok']};--info:{c['info']};
  --intelligence:{c['intelligence']};
  --sidebar-w:{w['sidebar_width']};--topbar-h:{w['top_bar_height']};
}}
*{{box-sizing:border-box}}
html{{background:var(--bg);color:var(--text);height:100%;overflow:hidden}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 {t['family']};letter-spacing:-0.01em;height:100%}}
a{{color:inherit;text-decoration:none;transition:all 200ms ease}}

.nv-shell{{display:grid;grid-template-columns:var(--sidebar-w) 1fr;height:100vh}}

/* LEFT SIDEBAR */
.nv-sidebar{{
  background:var(--surface);border-right:1px solid var(--line);
  display:flex;flex-direction:column;padding:32px 24px;
  height:100vh;overflow-y:auto;z-index:100;
}}
.nv-brand{{margin-bottom:48px;padding:0 8px}}
.nv-brand-title{{font-size:18px;font-weight:700;letter-spacing:-0.02em;color:var(--text);margin-bottom:4px}}
.nv-brand-sub{{font-size:11px;color:var(--subtle);text-transform:uppercase;letter-spacing:0.1em}}

.nv-nav{{display:grid;gap:8px}}
.nv-nav a,.nv-tab-label{{
  display:flex;align-items:center;gap:12px;min-height:44px;padding:0 16px;
  border-radius:var(--radius-md, 8px);color:var(--muted);font-weight:500;
}}
.nv-nav a:hover,.nv-tab-label:hover{{background:rgba(168, 154, 232, 0.05);color:var(--accent);box-shadow:inset 0 0 0 1px var(--line)}}
.nv-nav a.active,.nv-tab:checked + .nv-tab-label{{
  background:var(--panel);color:var(--accent);box-shadow:inset 4px 0 0 -1px var(--accent);
}}

/* MAIN AREA */
.nv-main{{display:flex;flex-direction:column;height:100vh;overflow:hidden}}

/* TOP INTELLIGENCE BAR */
.nv-top-bar{{
  height:var(--topbar-h);min-height:var(--topbar-h);
  border-bottom:1px solid var(--line);background:rgba(24, 21, 35, 0.8);
  backdrop-filter:blur(12px);padding:0 32px;
  display:flex;align-items:center;justify-content:space-between;
  z-index:90;
}}
.nv-breadcrumb{{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}}
.nv-breadcrumb span{{color:var(--text);font-weight:600}}

/* WORKSPACE AREA */
.nv-workspace{{flex:1;overflow-y:auto;padding:40px 48px;background:radial-gradient(circle at 50% 0%, rgba(168, 154, 232, 0.03), transparent 70%)}}

.nv-page-header{{margin-bottom:40px}}
.nv-page-title{{font-size:32px;font-weight:700;letter-spacing:-0.03em;margin:0 0 12px;color:var(--text)}}
.nv-subtitle{{font-size:16px;color:var(--muted);max-width:800px;line-height:1.6}}

.nv-grid{{display:grid;grid-template-columns:repeat(12, 1fr);gap:24px}}

/* CARDS / PANELS */
.nv-panel{{
  grid-column:span 12;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;transition:transform 250ms ease, box-shadow 250ms ease;
}}
.nv-panel:hover{{transform:translateY(-2px);box-shadow:0 12px 40px rgba(0,0,0,0.4)}}
.nv-panel-head{{
  padding:20px 24px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}}
.nv-panel-title{{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted)}}
.nv-panel-body{{padding:24px}}

/* DATA DISPLAY */
.nv-kv{{display:grid;grid-template-columns:200px 1fr;gap:12px 24px}}
.nv-k{{color:var(--muted);font-size:13px}}
.nv-v{{color:var(--text);font-family:{t['mono']};font-size:13px}}

.nv-table-wrap{{border:1px solid var(--line);border-radius:8px;overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;padding:14px 20px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--subtle);background:var(--panel)}}
td{{padding:14px 20px;border-top:1px solid var(--line);font-size:13px;color:var(--text)}}
tr:hover td{{background:rgba(168, 154, 232, 0.02)}}

/* BADGES */
.nv-badge{{
  display:inline-flex;align-items:center;padding:4px 12px;border-radius:99px;
  font-size:11px;font-weight:700;letter-spacing:0.02em;border:1px solid transparent;
}}
.nv-badge.info{{background:rgba(168, 154, 232, 0.1);color:var(--accent);border-color:rgba(168, 154, 232, 0.2)}}
.nv-badge.ok{{background:rgba(168, 154, 232, 0.1);color:var(--ok);border-color:rgba(168, 154, 232, 0.2)}}
.nv-badge.intelligence{{background:rgba(78, 228, 184, 0.1);color:var(--intelligence);border-color:rgba(78, 228, 184, 0.2)}}
.nv-badge.warning{{background:rgba(255, 184, 77, 0.1);color:var(--warning);border-color:rgba(255, 184, 77, 0.2)}}
.nv-badge.fail{{background:rgba(255, 85, 119, 0.1);color:var(--danger);border-color:rgba(255, 85, 119, 0.2)}}

.nv-intelligence{{color:var(--intelligence) !important}}

/* FORMS */
.nv-form{{display:grid;gap:20px;max-width:480px}}
.nv-field{{display:flex;flex-direction:column;gap:8px;font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em}}
input,select{{
  background:var(--bg);border:1px solid var(--line-strong);border-radius:8px;
  padding:12px 16px;color:var(--text);font-family:{t['family']};font-size:14px;
  transition:border-color 200ms ease, box-shadow 200ms ease;
}}
input:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 4px rgba(168, 154, 232, 0.1)}}

button,.nv-button{{
  background:var(--accent);color:var(--bg);border:none;border-radius:8px;
  padding:12px 24px;font-weight:700;font-size:14px;cursor:pointer;
  transition:transform 200ms ease, opacity 200ms ease;
}}
button:hover{{transform:translateY(-1px);opacity:0.9}}
button:active{{transform:translateY(0)}}

/* ALERTS */
.nv-alert{{
  padding:16px 24px;border-radius:12px;border:1px solid var(--line);
  margin-bottom:24px;font-size:14px;display:flex;align-items:center;gap:12px;
}}
.nv-alert.warning{{background:rgba(255, 184, 77, 0.05);border-color:rgba(255, 184, 77, 0.2);color:var(--warning)}}

/* STEPS / TIMELINE */
.nv-steps{{display:flex;flex-direction:column;gap:0;margin:0;padding:0;list-style:none;position:relative}}
.nv-step{{
  padding:0 0 32px 32px;border-left:2px solid var(--line);position:relative;
  color:var(--muted);transition:color 250ms ease;
}}
.nv-step::before{{
  content:'';position:absolute;left:-7px;top:4px;width:12px;height:12px;
  border-radius:50%;background:var(--surface);border:2px solid var(--line);
  transition:all 250ms ease;
}}
.nv-step.done{{color:var(--text)}}
.nv-step.done::before{{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 4px rgba(168, 154, 232, 0.2)}}
.nv-step:last-child{{border-left-color:transparent}}

/* FOOTER */
.nv-footer{{margin-top:auto;padding-top:40px;color:var(--subtle);font-size:12px;text-align:center}}

@media (max-width:1024px){{
  .nv-shell{{grid-template-columns:1fr}}
  .nv-sidebar{{display:none}}
}}
{extra}
"""


def badge(label: Any, state: Any = "info", theme: str = "") -> str:
    normalized = str(state or "info").lower()
    if normalized in {"true", "passed", "pass", "ok", "success"}:
        normalized = "ok"
    elif normalized in {"false", "failed", "fail", "error"}:
        normalized = "fail"
    if theme:
        normalized = theme
    return f'<span class="nv-badge {esc(normalized)}">{esc(label)}: {esc(state)}</span>'


def panel(title: str, body: str, *, class_name: str = "") -> str:
    cls = f"nv-panel {class_name}".strip()
    return (
        f'<section class="{cls}"><div class="nv-panel-head">'
        f'<div class="nv-panel-title">{esc(title)}</div></div>'
        f'<div class="nv-panel-body">{body}</div></section>'
    )


def render_section(section: dict) -> str:
    kind = section.get("kind") or section.get("type")
    title = section.get("title") or section.get("heading") or "Section"
    data = section.get("data", {})
    if kind == "alert":
        return f'<div class="nv-alert {esc(section.get("level", "info"))}">{esc(section.get("message"))}</div>'
    if kind == "kv":
        pairs = data.get("pairs", {})
        rows = section.get("rows")
        items = pairs.items() if isinstance(pairs, dict) else pairs
        if rows is not None:
            items = rows
        body = "".join(
            f'<div class="nv-k">{esc(k)}</div><div class="nv-v">{esc(v)}</div>' for k, v in items
        )
        return panel(title, f'<div class="nv-kv">{body}</div>')
    if kind == "table":
        headers = data.get("headers", section.get("columns", []))
        rows = data.get("rows", section.get("rows", []))
        head = "".join(f"<th>{esc(h)}</th>" for h in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        return panel(title, f'<div class="nv-table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    if kind == "badges":
        items = data.get("items", [])
        body = "".join(badge(item.get("label"), item.get("state")) for item in items)
        return panel(title, f'<div class="nv-badges">{body}</div>')
    if kind == "text":
        return panel(title, f"<p>{esc(data.get('body', section.get('text', '')))}</p>")
    if kind == "form":
        return render_form_section(section)
    if kind == "stages":
        steps = "".join(
            f'<li class="nv-step {"done" if st.get("done") else ""}">{esc(st.get("stage"))}</li>'
            for st in section.get("stages", [])
        )
        return panel(title, f'<ol class="nv-steps">{steps}</ol>')
    if kind == "list":
        items = section.get("items", [])
        body = "".join(f"<li>{esc(item)}</li>" for item in items) or "<li>No records available.</li>"
        return panel(title, f'<ul class="nv-items">{body}</ul>')
    if kind == "report":
        return panel(title, f"<pre>{esc(section.get('json', ''))}</pre>")
    if kind == "prose":
        cls = "nv-intelligence" if section.get("intelligence") else ""
        return panel(title, f"<p class='{cls}'>{esc(data.get('text', section.get('text', '')))}</p>")
    if kind == "timeline_records":
        items = section.get("items", [])
        intelligence = section.get("intelligence")
        body = "".join(
            f'<li class="nv-step done"><div style="font-weight:700;color:var(--text)">{esc(it.get("label"))}</div>'
            f'<div style="font-size:12px;color:var(--muted)">{esc(it.get("text"))}</div>'
            f'{badge("Status", it.get("status"), "intelligence" if intelligence else "ok")}</li>'
            for it in items
        )
        return panel(title, f'<ol class="nv-steps" style="margin-left:8px">{body}</ol>')
    return panel(title, "<p>No renderable content is available for this section.</p>")


def render_form_section(section: dict) -> str:
    form = section["form"]
    errors = {e["field"]: e["message"] for e in section.get("field_errors", [])}
    fields = []
    for field in form.get("fields", []):
        name = field.get("name", "")
        label = field.get("label", name)
        err = f'<span class="nv-error-text">{esc(errors[name])}</span>' if name in errors else ""
        if field.get("kind") == "select":
            opts = "".join(f'<option value="{esc(opt)}">{esc(opt)}</option>' for opt in field.get("options", []))
            control = f'<select name="{esc(name)}">{opts}</select>'
        elif field.get("kind") == "file":
            control = f'<input type="file" name="{esc(name)}">'
        else:
            typ = "password" if field.get("kind") == "password" else "text"
            ph = f' placeholder="{esc(field.get("placeholder"))}"' if field.get("placeholder") else ""
            control = f'<input type="{typ}" name="{esc(name)}"{ph}>'
        fields.append(f'<label class="nv-field">{esc(label)}{control}{err}</label>')
    body = (
        f'<form class="nv-form" method="{esc(form.get("method"))}" data-action="{esc(form.get("action"))}">'
        f'{"".join(fields)}<button type="submit">{esc(form.get("submit_label", "Submit"))}</button></form>'
    )
    return panel(section.get("heading", "Form"), body)


def _bar_svg(spec: dict) -> str:
    labels = spec.get("labels", [])
    values = [float(v) for v in spec.get("values", [])]
    if not values:
        return '<div class="nv-subtitle">No chart data available.</div>'
    vmin = float(spec.get("min", 0.0) or 0.0)
    vmax = float(spec.get("max") or max(max(values), 1.0))
    span = (vmax - vmin) or 1.0
    width, height, pad = 720, 250, 34
    bar_width = max(8, int((width - 2 * pad) / max(1, len(values)) * .62))
    gap = ((width - 2 * pad) - bar_width * len(values)) / max(1, len(values))
    parts = [f"<line x1='{pad}' y1='{height-pad}' x2='{width-pad}' y2='{height-pad}' stroke='rgba(168, 154, 232, 0.1)'/>"]
    for i, (label, value) in enumerate(zip(labels, values)):
        h = max(0.0, ((value - vmin) / span) * (height - 2 * pad))
        x = pad + i * (bar_width + gap)
        y = height - pad - h
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{h:.1f}' rx='3' fill='#A89AE8'/>")
        parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{height - 12}' fill='#8A8895' font-size='9' text-anchor='middle'>{esc(str(label)[:12])}</text>")
        parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{max(12, y - 5):.1f}' fill='#E6EBF8' font-size='9' text-anchor='middle'>{value:.3g}</text>")
    target = spec.get("target_line")
    if isinstance(target, (int, float)) and vmax:
        ty = height - pad - ((float(target) - vmin) / span) * (height - 2 * pad)
        parts.append(f"<line x1='{pad}' y1='{ty:.1f}' x2='{width-pad}' y2='{ty:.1f}' stroke='#FFB84D' stroke-dasharray='5 4'/>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _line_svg(spec: dict) -> str:
    points = spec.get("points", [])
    width, height, pad = 420, 300, 38
    parts = [f"<rect x='{pad}' y='{pad}' width='{width-2*pad}' height='{height-2*pad}' fill='none' stroke='rgba(168, 154, 232, 0.1)'/>"]
    if spec.get("diagonal"):
        parts.append(f"<line x1='{pad}' y1='{height-pad}' x2='{width-pad}' y2='{pad}' stroke='#5D5B6A' stroke-dasharray='3 4'/>")
    coords = []
    for point in points:
        x, y = point.get("x"), point.get("y")
        if x is None or y is None:
            continue
        px = pad + float(x) * (width - 2 * pad)
        py = height - pad - float(y) * (height - 2 * pad)
        coords.append((px, py))
    if len(coords) > 1:
        parts.append("<polyline fill='none' stroke='#4EE4B8' stroke-width='2' points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords) + "'/>")
    for x, y in coords:
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.2' fill='#A89AE8'/>")
    parts.append(f"<text x='{width/2:.0f}' y='{height-9}' fill='#8A8895' font-size='10' text-anchor='middle'>{esc(spec.get('x_label', 'x'))}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _graph_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    width, row_h = 760, 58
    height = max(150, 40 + row_h * max(1, len(nodes)))
    positions = {}
    for i, node in enumerate(nodes):
        positions[node.get("id")] = (84 + (i % 3) * 245, 38 + i * row_h)
    parts = []
    for edge in edges:
        src, dst = positions.get(edge.get("from")), positions.get(edge.get("to"))
        if src and dst:
            parts.append(f"<line x1='{src[0]}' y1='{src[1]}' x2='{dst[0]}' y2='{dst[1]}' stroke='rgba(168, 154, 232, 0.1)'/>")
    for node in nodes:
        x, y = positions.get(node.get("id"), (0, 0))
        parts.append(f"<circle cx='{x}' cy='{y}' r='9' fill='#A89AE8'/>")
        parts.append(f"<text x='{x+15}' y='{y+4}' fill='#E6EBF8' font-size='11'>{esc(node.get('label'))} <tspan fill='#8A8895'>{esc(node.get('short', ''))}</tspan></text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _timeline_svg(spec: dict) -> str:
    events = spec.get("events", [])
    width, height, pad = 760, 108, 34
    if not events:
        return '<div class="nv-subtitle">No timeline events available.</div>'
    step = (width - 2 * pad) / max(1, min(len(events), 80) - 1)
    parts = [f"<line x1='{pad}' y1='{height/2}' x2='{width-pad}' y2='{height/2}' stroke='rgba(168, 154, 232, 0.1)'/>"]
    for i, event in enumerate(events[:80]):
        x = pad + i * step
        parts.append(f"<circle cx='{x:.1f}' cy='{height/2}' r='4.2' fill='#A89AE8'/>")
        if i % 5 == 0:
            parts.append(f"<text x='{x:.1f}' y='{height/2-10:.1f}' fill='#8A8895' font-size='8' text-anchor='middle'>{esc(event.get('seq', i))}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _layout_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    width, height = 420, 300
    parts = []
    for node in nodes:
        x = float(node.get("x", .5)) * width
        y = float(node.get("y", .5)) * height
        color = "#A89AE8"
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='9' fill='{color}'/>")
        parts.append(f"<text x='{x:.1f}' y='{y-13:.1f}' fill='#E6EBF8' font-size='10' text-anchor='middle'>{esc(node.get('label'))}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _brain_simulation_svg() -> str:
    """A high-fidelity, CSS-animated SVG brain simulation."""
    # Simplified anatomical paths for two hemispheres
    l_hemi = "M150,100 C100,100 80,150 80,200 C80,280 150,320 150,320 C150,320 150,100 150,100"
    r_hemi = "M150,100 C200,100 220,150 220,200 C220,280 150,320 150,320 C150,320 150,100 150,100"

    # Internal neural network (nodes and synapses)
    nodes = [
        (120, 150, 0), (180, 150, 0.5), (105, 200, 0.2), (195, 200, 0.7),
        (130, 250, 0.4), (170, 250, 0.9), (150, 180, 0.1), (150, 280, 0.6)
    ]
    edges = [
        (120, 150, 105, 200), (180, 150, 195, 200), (105, 200, 130, 250),
        (195, 200, 170, 250), (130, 250, 150, 280), (170, 250, 150, 280),
        (150, 180, 120, 150), (150, 180, 180, 150)
    ]

    svg_parts = [
        '<style>',
        '@keyframes brain-pulse { 0%, 100% { opacity: 0.3; transform: scale(1); } 50% { opacity: 0.8; transform: scale(1.1); } }',
        '@keyframes synapse-flow { 0% { stroke-dashoffset: 20; } 100% { stroke-dashoffset: 0; } }',
        '@keyframes brain-glow { 0%, 100% { filter: drop-shadow(0 0 5px rgba(168, 154, 232, 0.2)); } 50% { filter: drop-shadow(0 0 15px rgba(168, 154, 232, 0.5)); } }',
        '.hemi { fill: rgba(168, 154, 232, 0.03); stroke: rgba(168, 154, 232, 0.1); stroke-width: 1; }',
        '.node { fill: var(--accent); animation: brain-pulse 3s infinite ease-in-out; }',
        '.edge { fill: none; stroke: rgba(78, 228, 184, 0.2); stroke-width: 1; stroke-dasharray: 4 4; animation: synapse-flow 1s infinite linear; }',
        '#brain-sim { animation: brain-glow 4s infinite ease-in-out; }',
        '</style>',
        '<g id="brain-sim">',
        f'<path class="hemi" d="{l_hemi}"/>',
        f'<path class="hemi" d="{r_hemi}"/>'
    ]

    for x1, y1, x2, y2 in edges:
        svg_parts.append(f'<path class="edge" d="M{x1},{y1} L{x2},{y2}"/>')

    for x, y, delay in nodes:
        svg_parts.append(f'<circle class="node" cx="{x}" cy="{y}" r="3" style="animation-delay: {delay}s"/>')

    svg_parts.append('</g>')

    return f'<svg width="300" height="400" viewBox="0 50 300 300" style="margin: 0 auto; display: block;">{"".join(svg_parts)}</svg>'


def render_visualization(viz: dict) -> str:
    typ = viz.get("type")
    spec = viz.get("spec", {})
    if typ == "bar":
        body = _bar_svg(spec)
    elif typ == "line":
        body = _line_svg(spec)
    elif typ == "graph":
        body = _graph_svg(spec)
    elif typ == "timeline":
        body = _timeline_svg(spec)
    elif typ == "layout":
        body = _layout_svg(spec)
    elif typ == "table":
        body = render_section({"kind": "table", "title": viz.get("title", "Table"), "data": spec})
        return body
    elif typ == "timeline_records":
        body = render_section({"kind": "timeline_records", "title": viz.get("title", "Timeline"), "items": spec.get("items", [])})
        return body
    else:
        body = '<div class="nv-subtitle">Unsupported visualization spec.</div>'
    return panel(viz.get("title", "Visualization"), f'<div class="nv-viz">{body}</div>')


def render_controls(controls: list[dict]) -> str:
    if not controls:
        return ""
    body = []
    for control in controls:
        disabled = "" if control.get("enabled", True) else " disabled"
        body.append(
            f'<div class="nv-control{disabled}">'
            f'<div class="nv-panel-title">{esc(control.get("action"))}</div>'
            f'<div class="nv-subtitle">target {esc(control.get("target_kind"))}: '
            f'{esc(control.get("target_id"))}</div>'
            f'<div class="nv-badges">'
            f'{badge("authorization", control.get("requires_authorization"))}'
            f'{badge("audit", control.get("generates_audit"))}'
            f'{badge("lineage", control.get("generates_lineage"))}'
            f'{badge("governance", control.get("generates_governance_record"))}'
            f'</div><div class="nv-subtitle">{esc(control.get("rationale"))}</div></div>'
        )
    return panel("Governed Intervention Controls", f'<div class="nv-controls">{"".join(body)}</div>')


def render_application_page(page: dict, *, version: str) -> str:
    nav = page.get("nav", [])
    title = page.get("title", "NeuroVision")
    subtitle = page.get("subtitle", "")
    flash = render_section({"type": "alert", **page["flash"]}) if page.get("flash") else ""
    sections = "".join(render_section(section) for section in page.get("sections", []))

    # Brain simulation in the Command Center (Screen 1)
    brain = ""
    if page.get("id") == "dashboard":
        brain = f'<div style="grid-column: span 12; margin-bottom: 40px; background: var(--surface); border-radius: 24px; padding: 48px; border: 1px solid var(--line); box-shadow: inset 0 0 80px rgba(168, 154, 232, 0.05);">{_brain_simulation_svg()}</div>'
    nav_html = "".join(
        f'<a class="{"active" if item.get("active") else ""}" href="#{esc(item.get("id"))}">{esc(item.get("label"))}</a>'
        for item in nav
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title><style>{css()}</style></head><body>"
        '<div class="nv-shell"><aside class="nv-sidebar">'
        '<div class="nv-brand"><div class="nv-brand-title">NeuroVision</div>'
        '<div class="nv-brand-sub">Intelligence Operating Environment</div></div>'
        f'<nav><div class="nv-nav">{nav_html}</div></nav></aside>'
        '<main class="nv-main">'
        '<header class="nv-top-bar">'
        '<div class="nv-breadcrumb">Workspace / <span>' + esc(title) + '</span></div>'
        f'<div class="nv-meta">{badge("backend", "v1")}{badge("version", version)}</div>'
        '</header>'
        '<div class="nv-workspace">'
        '<div class="nv-page-header">'
        f'<h1 class="nv-page-title">{esc(title)}</h1>'
        f'<p class="nv-subtitle">{esc(subtitle)}</p>'
        '</div>'
        f'<div class="nv-grid">{flash}{brain}{sections}</div>'
        '<div class="nv-footer">Intelligence Operating Environment &bull; Lore Protocol Compliant</div>'
        '</div>'
        '</main></div></body></html>'
    )


def _page_html(page: dict) -> str:
    content = "".join(render_section(section) for section in page.get("sections", []))
    content += "".join(render_visualization(viz) for viz in page.get("visualizations", []))
    content += render_controls(page.get("controls", []))
    return (
        '<div class="nv-page-header">'
        f'<h2 class="nv-page-title">{esc(page.get("title"))}</h2>'
        '</div>'
        f'<div class="nv-grid">{content}</div>'
    )


def render_workstation_view(view: Any, *, title: str, subtitle: str, version: str) -> str:
    data = view.to_dict() if hasattr(view, "to_dict") else view
    areas = data.get("areas", [])
    validation = data.get("validation", {})
    meta = data.get("meta", {})
    reveal = "".join(
        f"#tab-{esc(area.get('id'))}:checked ~ .nv-main #area-{esc(area.get('id'))}{{display:block}}"
        f"#tab-{esc(area.get('id'))}:checked ~ .nv-sidebar label[for='tab-{esc(area.get('id'))}']"
        "{background:var(--panel);color:var(--accent);box-shadow:inset 4px 0 0 -1px var(--accent)}"
        for area in areas
    )
    radios = []
    labels = []
    panels = []
    for index, area in enumerate(areas):
        checked = " checked" if index == 0 else ""
        aid = esc(area.get("id"))
        radios.append(f"<input class='tab' type='radio' name='tabs' id='tab-{aid}'{checked}>")
        labels.append(f'<label class="nv-tab-label" for="tab-{aid}">{esc(area.get("title"))}</label>')
        pagebar = "".join(f'<span class="nv-badge info" style="margin-right:8px">{esc(page.get("title"))}</span>' for page in area.get("pages", []))
        pages = "".join(_page_html(page) for page in area.get("pages", []))
        panels.append(f'<section class="nv-area" id="area-{aid}"><div style="margin-bottom:24px">{pagebar}</div>{pages}</section>')
    meta_badges = [
        badge("validation", "ok" if validation.get("ok") else "failed"),
        badge("version", version),
    ]
    for key in ("n_cases", "n_events", "n_goals", "n_workflows", "n_reports", "governance_health"):
        if key in meta:
            meta_badges.append(badge(key, meta.get(key)))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title><style>{css(reveal)}</style></head><body>"
        f'<div class="nv-shell">{"".join(radios)}<aside class="nv-sidebar">'
        '<div class="nv-brand"><div class="nv-brand-title">NeuroVision</div>'
        f'<div class="nv-brand-sub">{esc(subtitle)}</div></div><nav class="nv-nav">{"".join(labels)}</nav></aside>'
        '<main class="nv-main">'
        '<header class="nv-top-bar">'
        '<div class="nv-breadcrumb">Workstation / <span>' + esc(title) + '</span></div>'
        f'<div class="nv-meta">{"".join(meta_badges)}</div>'
        '</header>'
        '<div class="nv-workspace">'
        '<div class="nv-page-header">'
        f'<h1 class="nv-page-title">{esc(title)}</h1><p class="nv-subtitle">{esc(subtitle)}</p>'
        '</div>'
        f'{"".join(panels)}'
        '<div class="nv-footer">Deterministic Static Workstation &bull; Lore Protocol Compliant</div>'
        '</div>'
        '</main></div></body></html>'
    )


def render_research_view(view: Any, *, title: str, subtitle: str, version: str) -> str:
    data = view.to_dict() if hasattr(view, "to_dict") else view
    pages = data.get("pages", [])
    validation = data.get("validation", {})
    meta = data.get("meta", {})
    reveal = "".join(
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-main #area-{esc(page.get('id'))}{{display:block}}"
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-sidebar label[for='tab-{esc(page.get('id'))}']"
        "{background:var(--panel);color:var(--accent);box-shadow:inset 0 4px 0 -1px var(--accent)}"
        for page in pages
    )
    radios = []
    labels = []
    panels = []
    for index, page in enumerate(pages):
        checked = " checked" if index == 0 else ""
        pid = esc(page.get("id"))
        radios.append(f"<input class='tab' type='radio' name='tabs' id='tab-{pid}'{checked}>")
        labels.append(f'<label class="nv-tab-label" for="tab-{pid}">{esc(page.get("title"))}</label>')
        panels.append(f'<section class="nv-area" id="area-{pid}">{_page_html(page)}</section>')
    meta_badges = [badge("validation", "ok" if validation.get("ok") else "failed"), badge("version", version)]
    for key in ("inference_id", "lineage_id"):
        if key in meta:
            meta_badges.append(badge(key, meta.get(key)))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title><style>{css(reveal)}</style></head><body>"
        f'<div class="nv-shell">{"".join(radios)}<aside class="nv-sidebar">'
        '<div class="nv-brand"><div class="nv-brand-title">NeuroVision</div>'
        f'<div class="nv-brand-sub">{esc(subtitle)}</div></div><nav class="nv-nav">{"".join(labels)}</nav></aside>'
        '<main class="nv-main">'
        '<header class="nv-top-bar">'
        '<div class="nv-breadcrumb">Research / <span>' + esc(title) + '</span></div>'
        f'<div class="nv-meta">{"".join(meta_badges)}</div>'
        '</header>'
        '<div class="nv-workspace">'
        '<div class="nv-page-header">'
        f'<h1 class="nv-page-title">{esc(title)}</h1><p class="nv-subtitle">{esc(subtitle)}</p>'
        '</div>'
        f'{"".join(panels)}'
        '<div class="nv-footer">Offline Deterministic Research Environment &bull; Lore Protocol Compliant</div>'
        '</div>'
        '</main></div></body></html>'
    )


__all__ = [
    "THEME_TOKENS",
    "badge",
    "css",
    "esc",
    "panel",
    "render_application_page",
    "render_controls",
    "render_research_view",
    "render_section",
    "render_visualization",
    "render_workstation_view",
]
