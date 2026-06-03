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
        "line": "rgba(168, 154, 232, 0.12)",
        "line_strong": "rgba(168, 154, 232, 0.2)",
        "text": "#F5F5FA",
        "muted": "#9C97B5",
        "subtle": "#6D6786",
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
    "radius": {"sm": "4px", "md": "8px", "lg": "24px"},
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
  border-bottom:1px solid var(--line);background:rgba(18, 16, 27, 0.8);
  backdrop-filter:blur(24px);padding:0 32px;
  display:flex;align-items:center;justify-content:space-between;
  z-index:90;
}}
.nv-breadcrumb{{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}}
.nv-breadcrumb span{{color:var(--text);font-weight:600}}

/* WORKSPACE AREA */
.nv-workspace{{flex:1;overflow-y:auto;padding:40px 48px;background:radial-gradient(circle at 50% 0%, rgba(168, 154, 232, 0.03), transparent 70%)}}

/* WORKSTATION LAYOUT */
.nv-workstation-layout{{
  display:grid;grid-template-columns:1fr 320px;grid-template-rows:1fr auto;gap:24px;height:100%;
}}
.nv-ws-center{{grid-column:1;grid-row:1}}
.nv-ws-right{{grid-column:2;grid-row:1 / span 2;display:flex;flex-direction:column;gap:24px}}
.nv-ws-bottom{{grid-column:1;grid-row:2;padding-top:24px;border-top:1px solid var(--line)}}

.nv-area{{display:none;height:100%}}

.nv-page-header{{margin-bottom:40px}}
.nv-page-title{{font-size:32px;font-weight:700;letter-spacing:-0.03em;margin:0 0 12px;color:var(--text)}}
.nv-subtitle{{font-size:16px;color:var(--muted);max-width:800px;line-height:1.6}}

.nv-grid{{display:grid;grid-template-columns:repeat(12, 1fr);gap:24px}}

/* CARDS / PANELS */
.nv-panel{{
  grid-column:span 12;background:var(--surface);border:1px solid var(--line);
  border-radius:24px;overflow:hidden;transition:transform 250ms ease, box-shadow 250ms ease;
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
    if kind == "visualization":
        return render_visualization({
            "type": section.get("visualization_type"),
            "title": title,
            "spec": section.get("spec", {})
        })
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
        f'<form class="nv-form" method="{esc(form.get("method"))}" action="/action/{esc(form.get("action"))}" enctype="{"multipart/form-data" if any(f.get("kind") == "file" for f in form.get("fields", [])) else "application/x-www-form-urlencoded"}">'
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


def _brain_simulation_html() -> str:
    """A high-fidelity, animated Canvas-based living brain simulation."""
    return """
<div id="brain-container" style="width:100%; height:600px; position:relative; overflow:hidden; background: radial-gradient(circle at 50% 50%, rgba(168, 154, 232, 0.05) 0%, transparent 70%); border-radius: 24px;">
    <canvas id="brain-canvas" style="width:100%; height:100%;"></canvas>
    <div id="brain-overlay" style="position:absolute; top:24px; left:24px; pointer-events:none;">
        <div class="nv-brand-sub" style="color:var(--accent-2); margin-bottom:8px;">Live Neural Flow</div>
        <div id="active-region" style="font-size:24px; font-weight:700; color:var(--text); letter-spacing:-0.02em;">Frontal Lobe</div>
    </div>
    <div style="position:absolute; bottom:24px; right:24px; text-align:right;">
        <div class="nv-badge intelligence">Confidence: 99.2%</div>
        <div style="margin-top:8px; font-size:10px; color:var(--subtle); text-transform:uppercase; letter-spacing:0.1em;">Real-time Telemetry</div>
    </div>
</div>
<script>
(function() {
    const canvas = document.getElementById('brain-canvas');
    const ctx = canvas.getContext('2d');
    const container = document.getElementById('brain-container');
    let width, height, dpr;

    function resize() {
        dpr = window.devicePixelRatio || 1;
        width = container.clientWidth;
        height = container.clientHeight;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);
    }
    window.addEventListener('resize', resize);
    resize();

    const nodes = [];
    const edges = [];
    const particles = [];
    const nodeCount = 220;
    const edgeCount = 450;

    // Generate nodes in a brain-like shape
    for (let i = 0; i < nodeCount; i++) {
        let x, y;
        const side = Math.random() > 0.5 ? 1 : -1;
        // Two lobes approximation
        const centerX = width / 2 + (side * width * 0.12);
        const centerY = height / 2;
        const angle = Math.random() * Math.PI * 2;
        const radiusX = (0.2 + Math.random() * 0.15) * width;
        const radiusY = (0.25 + Math.random() * 0.2) * height;

        x = centerX + Math.cos(angle) * radiusX * Math.random();
        y = centerY + Math.sin(angle) * radiusY * Math.random();

        nodes.push({
            x, y,
            baseX: x, baseY: y,
            vx: (Math.random() - 0.5) * 0.2,
            vy: (Math.random() - 0.5) * 0.2,
            size: 1 + Math.random() * 2,
            pulse: Math.random() * Math.PI * 2,
            region: getRegionName(x, y, width, height)
        });
    }

    function getRegionName(x, y, w, h) {
        const cx = w/2, cy = h/2;
        if (y < cy - h*0.1) return 'Frontal';
        if (y > cy + h*0.15) return 'Occipital';
        if (x < cx - w*0.1) return 'Temporal (L)';
        if (x > cx + w*0.1) return 'Temporal (R)';
        return 'Parietal';
    }

    // Connect nodes
    for (let i = 0; i < edgeCount; i++) {
        const a = nodes[Math.floor(Math.random() * nodes.length)];
        let b = nodes[Math.floor(Math.random() * nodes.length)];
        const distSq = (a.x - b.x)**2 + (a.y - b.y)**2;
        if (distSq < (width * 0.15)**2 && a !== b) {
            edges.push({a, b, strength: 0.1 + Math.random() * 0.4});
        } else {
            i--; // try again
        }
    }

    function animate(time) {
        ctx.clearRect(0, 0, width, height);
        const breathing = 1 + Math.sin(time / 1500) * 0.02;

        // Update nodes
        nodes.forEach(n => {
            n.x = width/2 + (n.baseX - width/2) * breathing + Math.sin(time/1000 + n.pulse) * 2;
            n.y = height/2 + (n.baseY - height/2) * breathing + Math.cos(time/1000 + n.pulse) * 2;
        });

        // Draw edges
        ctx.lineWidth = 0.5;
        edges.forEach(e => {
            const alpha = 0.05 + Math.sin(time/500 + e.a.pulse) * 0.05;
            ctx.strokeStyle = `rgba(168, 154, 232, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(e.a.x, e.a.y);
            ctx.lineTo(e.b.x, e.b.y);
            ctx.stroke();
        });

        // Neural Flow Particles
        if (Math.random() < 0.1) {
            const edge = edges[Math.floor(Math.random() * edges.length)];
            particles.push({edge, progress: 0, speed: 0.005 + Math.random() * 0.01});
        }

        particles.forEach((p, i) => {
            p.progress += p.speed;
            if (p.progress >= 1) {
                particles.splice(i, 1);
                return;
            }
            const x = p.edge.a.x + (p.edge.b.x - p.edge.a.x) * p.progress;
            const y = p.edge.a.y + (p.edge.b.y - p.edge.a.y) * p.progress;
            ctx.fillStyle = '#4EE4B8';
            ctx.beginPath();
            ctx.arc(x, y, 1.5, 0, Math.PI*2);
            ctx.fill();
            // Glow
            ctx.shadowBlur = 4;
            ctx.shadowColor = '#4EE4B8';
            ctx.fill();
            ctx.shadowBlur = 0;
        });

        // Draw nodes
        nodes.forEach(n => {
            const active = Math.sin(time/1000 + n.pulse) > 0.8;
            ctx.fillStyle = active ? '#4EE4B8' : '#A89AE8';
            ctx.globalAlpha = active ? 0.8 : 0.3;
            ctx.beginPath();
            ctx.arc(n.x, n.y, active ? n.size * 1.5 : n.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1.0;

        requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
})();
</script>
"""


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
        brain = f'<div style="grid-column: span 12; margin-bottom: 40px; background: var(--surface); border-radius: 24px; padding: 48px; border: 1px solid var(--line); box-shadow: inset 0 0 80px rgba(168, 154, 232, 0.05);">{_brain_simulation_html()}</div>'
    nav_html = "".join(
        f'<a class="{"active" if item.get("active") else ""}" href="/{esc(item.get("id"))}">{esc(item.get("label"))}</a>'
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
        f"#tab-{esc(area.get('id'))}:checked ~ .nv-main #area-{esc(area.get('id'))}{{display:grid}}"
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

        # Workstation 3-Part Layout: Center, Right, Bottom
        pages_list = area.get("pages", [])
        center_pages = [p for p in pages_list if "overview" in p.get("id", "").lower() or "graph" in p.get("id", "").lower() or "workspace" in p.get("title", "").lower()]
        right_pages = [p for p in pages_list if "insight" in p.get("title", "").lower() or "alert" in p.get("title", "").lower() or "governance" in p.get("title", "").lower()]
        bottom_pages = [p for p in pages_list if "finding" in p.get("title", "").lower() or "telemetry" in p.get("title", "").lower() or "timeline" in p.get("title", "").lower()]

        # Fallback
        if not center_pages and pages_list: center_pages = [pages_list[0]]
        if not right_pages and len(pages_list) > 1: right_pages = [pages_list[1]]
        if not bottom_pages and len(pages_list) > 2: bottom_pages = [pages_list[2]]

        center_html = "".join(_page_html(p) for p in center_pages)
        right_html = "".join(_page_html(p) for p in right_pages)
        bottom_html = "".join(_page_html(p) for p in bottom_pages)

        area_layout = f"""
        <div class="nv-workstation-layout">
            <div class="nv-ws-center">{center_html}</div>
            <div class="nv-ws-right">{right_html}</div>
            <div class="nv-ws-bottom">{bottom_html}</div>
        </div>
        """
        panels.append(f'<section class="nv-area" id="area-{aid}">{area_layout}</section>')
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
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-main #area-{esc(page.get('id'))}{{display:grid}}"
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-sidebar label[for='tab-{esc(page.get('id'))}']"
        "{background:var(--panel);color:var(--accent);box-shadow:inset 4px 0 0 -1px var(--accent)}"
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

        # Research layout: Center (Object), Right (Hypotheses/Notes), Bottom (Metrics)
        sections = page.get("sections", [])
        center_secs = [s for s in sections if s.get("type") in ("graph", "visualization", "layout", "report")]
        right_secs = [s for s in sections if "hypotheses" in s.get("title", "").lower() or "notes" in s.get("title", "").lower() or "insights" in s.get("title", "").lower() or "lineage" in s.get("title", "").lower()]
        bottom_secs = [s for s in sections if "metrics" in s.get("title", "").lower() or "benchmarks" in s.get("title", "").lower() or "experiments" in s.get("title", "").lower() or "audit" in s.get("title", "").lower()]

        # Fallback
        if not center_secs and sections: center_secs = [sections[0]]
        if not right_secs and len(sections) > 1: right_secs = [sections[1]]
        if not bottom_secs and len(sections) > 2: bottom_secs = [sections[2]]

        def _render_secs(secs):
            return "".join(render_section(s) for s in secs)

        area_layout = f"""
        <div class="nv-workstation-layout">
            <div class="nv-ws-center">{_render_secs(center_secs)}</div>
            <div class="nv-ws-right">{_render_secs(right_secs)}</div>
            <div class="nv-ws-bottom">{_render_secs(bottom_secs)}</div>
        </div>
        """
        panels.append(f'<section class="nv-area" id="area-{pid}">{area_layout}</section>')
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
