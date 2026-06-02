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
        "bg": "#080d12",
        "surface": "#0d141b",
        "panel": "#111b24",
        "panel_2": "#16222d",
        "line": "#263440",
        "line_strong": "#385061",
        "text": "#e6edf3",
        "muted": "#9aa8b4",
        "subtle": "#6f7f8e",
        "accent": "#67b7dc",
        "accent_2": "#77d0a5",
        "warning": "#e2b15f",
        "danger": "#ef6f6c",
        "ok": "#73d29c",
        "info": "#8fb7ff",
    },
    "typography": {
        "family": "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif",
        "mono": "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace",
    },
    "spacing": {"1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "20px", "6": "24px"},
    "radius": {"sm": "4px", "md": "6px", "lg": "8px"},
    "elevation": {"panel": "0 12px 34px rgba(0,0,0,.24)"},
    "animation": {"fast": "120ms ease", "standard": "180ms ease"},
    "interaction": {"focus": "0 0 0 3px rgba(103,183,220,.26)"},
    "accessibility": {"min_contrast": "AA", "focus_visible": True},
    "status": {"ok": "ok", "warning": "warning", "danger": "danger", "info": "info"},
    "chart": {"bar": "#67b7dc", "line": "#77d0a5", "grid": "#263440"},
    "workspace": {"sidebar_width": "248px", "content_max": "1440px"},
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
    return f"""
:root{{
  --bg:{c['bg']};--surface:{c['surface']};--panel:{c['panel']};--panel-2:{c['panel_2']};
  --line:{c['line']};--line-strong:{c['line_strong']};--text:{c['text']};--muted:{c['muted']};
  --subtle:{c['subtle']};--accent:{c['accent']};--accent-2:{c['accent_2']};
  --warning:{c['warning']};--danger:{c['danger']};--ok:{c['ok']};--info:{c['info']};
}}
*{{box-sizing:border-box}}
html{{background:var(--bg);color:var(--text)}}
body{{margin:0;background:
  radial-gradient(circle at 20% 0%, rgba(103,183,220,.10), transparent 30%),
  linear-gradient(180deg,#0a1016 0%,#080d12 58%,#070b10 100%);
  color:var(--text);font:13px/1.5 {t['family']};letter-spacing:0}}
a{{color:inherit;text-decoration:none}}
.nv-shell{{min-height:100vh;display:grid;grid-template-columns:minmax(210px,248px) 1fr}}
.nv-sidebar{{border-right:1px solid var(--line);background:rgba(13,20,27,.92);padding:18px 14px;position:sticky;top:0;height:100vh;overflow:auto}}
.nv-brand{{display:grid;gap:3px;padding:0 8px 18px;border-bottom:1px solid var(--line)}}
.nv-brand-title{{font-size:16px;font-weight:700;color:var(--text)}}
.nv-brand-sub{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.nv-nav{{display:grid;gap:5px;margin-top:16px}}
.nv-nav a,.nv-tab-label{{display:flex;align-items:center;gap:8px;min-height:34px;padding:8px 10px;border:1px solid transparent;border-radius:6px;color:var(--muted);transition:background 120ms ease,border-color 120ms ease,color 120ms ease}}
.nv-nav a.active,.nv-tab:checked + .nv-tab-label{{background:rgba(103,183,220,.10);border-color:rgba(103,183,220,.34);color:var(--text)}}
.nv-nav a:hover,.nv-tab-label:hover{{background:rgba(255,255,255,.035);color:var(--text)}}
.nv-main{{min-width:0;padding:20px 22px 28px}}
.nv-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}}
.nv-page-title{{margin:0;font-size:23px;line-height:1.16;font-weight:700;color:var(--text)}}
.nv-subtitle{{margin:6px 0 0;color:var(--muted);font-size:13px;max-width:760px}}
.nv-meta{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;color:var(--muted);font-family:{t['mono']};font-size:11px}}
.nv-grid{{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px}}
.nv-panel{{grid-column:span 12;background:linear-gradient(180deg,rgba(22,34,45,.98),rgba(13,20,27,.98));border:1px solid var(--line);border-radius:8px;box-shadow:0 12px 34px rgba(0,0,0,.22);overflow:hidden}}
.nv-panel-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:42px;padding:11px 13px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.018)}}
.nv-panel-title{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#c8d4df;font-weight:700}}
.nv-panel-body{{padding:13px;overflow:auto}}
.nv-kv{{display:grid;grid-template-columns:minmax(150px,260px) minmax(0,1fr);gap:7px 14px}}
.nv-k{{color:var(--muted)}}
.nv-v{{font-family:{t['mono']};word-break:break-word;color:#e9f2f8}}
.nv-table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:6px}}
table{{width:100%;border-collapse:collapse;min-width:520px}}
th,td{{padding:8px 9px;border-bottom:1px solid rgba(38,52,64,.78);text-align:left;vertical-align:top}}
th{{color:#b9c8d4;font-size:11px;text-transform:uppercase;letter-spacing:.07em;background:rgba(255,255,255,.026);font-weight:700}}
td{{color:#d8e3eb}}
tr:last-child td{{border-bottom:0}}
.nv-badges{{display:flex;flex-wrap:wrap;gap:6px}}
.nv-badge{{display:inline-flex;align-items:center;gap:6px;min-height:24px;padding:3px 8px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.035);color:var(--muted);font-size:11px;font-weight:650}}
.nv-badge.ok,.nv-badge.pass,.nv-badge.success{{border-color:rgba(115,210,156,.52);color:var(--ok);background:rgba(115,210,156,.10)}}
.nv-badge.fail,.nv-badge.error,.nv-badge.danger{{border-color:rgba(239,111,108,.52);color:var(--danger);background:rgba(239,111,108,.10)}}
.nv-badge.warning{{border-color:rgba(226,177,95,.58);color:var(--warning);background:rgba(226,177,95,.10)}}
.nv-badge.info{{border-color:rgba(143,183,255,.48);color:var(--info);background:rgba(143,183,255,.10)}}
.nv-alert{{margin-bottom:12px;padding:11px 13px;border-radius:8px;border:1px solid var(--line);background:rgba(255,255,255,.035);color:var(--text)}}
.nv-alert.success{{border-color:rgba(115,210,156,.52);background:rgba(115,210,156,.10)}}
.nv-alert.warning{{border-color:rgba(226,177,95,.58);background:rgba(226,177,95,.10)}}
.nv-alert.error{{border-color:rgba(239,111,108,.52);background:rgba(239,111,108,.10)}}
.nv-form{{display:grid;gap:12px;max-width:560px}}
.nv-field{{display:grid;gap:6px;color:#c9d6df;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}}
input,select{{width:100%;min-height:38px;padding:8px 10px;border-radius:6px;border:1px solid var(--line-strong);background:#091018;color:var(--text);font:13px {t['family']}}}
input:focus,select:focus,button:focus-visible,a:focus-visible,label:focus-visible{{outline:0;box-shadow:0 0 0 3px rgba(103,183,220,.26)}}
button,.nv-button{{display:inline-flex;align-items:center;justify-content:center;gap:8px;width:max-content;min-height:36px;padding:8px 12px;border-radius:6px;border:1px solid rgba(103,183,220,.42);background:linear-gradient(180deg,#1d5f7c,#16485f);color:white;font-weight:700;cursor:pointer}}
.nv-error-text{{color:var(--danger);font-size:12px;text-transform:none;letter-spacing:0;font-weight:500}}
.nv-steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:8px;list-style:none;margin:0;padding:0}}
.nv-step{{border:1px solid var(--line);border-radius:6px;padding:9px 10px;background:rgba(255,255,255,.025);color:var(--muted)}}
.nv-step.done{{border-color:rgba(115,210,156,.55);background:rgba(115,210,156,.10);color:var(--ok)}}
.nv-items{{margin:0;padding-left:18px;color:#dbe6ee}}
pre{{margin:0;max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:6px;background:#070c11;color:#dbe6ee;padding:12px;font:12px/1.45 {t['mono']}}}
.nv-viz svg{{max-width:100%;height:auto;background:#070c11;border:1px solid var(--line);border-radius:6px}}
.nv-tabs{{display:grid;grid-template-columns:248px 1fr;gap:0;min-height:100vh}}
.nv-tab-rail{{border-right:1px solid var(--line);background:rgba(13,20,27,.92);padding:18px 14px;position:sticky;top:0;height:100vh;overflow:auto}}
.nv-tab,.tab{{position:absolute;left:-9999px}}
.nv-panels{{padding:20px 22px}}
.nv-area{{display:none}}
.nv-pagebar{{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}}
.nv-page-chip{{display:inline-flex;padding:4px 8px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:11px;background:rgba(255,255,255,.025)}}
.nv-controls{{display:grid;gap:8px;margin-top:10px}}
.nv-control{{border:1px solid rgba(226,177,95,.42);border-radius:6px;padding:9px 10px;background:rgba(226,177,95,.08)}}
.nv-control.disabled{{opacity:.55}}
.nv-footer{{color:var(--subtle);font-size:11px;text-align:right;margin-top:20px}}
@media (max-width:860px){{
  .nv-shell,.nv-tabs{{grid-template-columns:1fr}}
  .nv-sidebar,.nv-tab-rail{{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--line)}}
  .nv-main,.nv-panels{{padding:16px}}
  .nv-kv{{grid-template-columns:1fr}}
  .nv-top{{display:grid}}
  .nv-meta{{justify-content:flex-start}}
}}
{extra}
"""


def badge(label: Any, state: Any = "info") -> str:
    normalized = str(state or "info").lower()
    if normalized in {"true", "passed", "pass", "ok", "success"}:
        normalized = "ok"
    elif normalized in {"false", "failed", "fail", "error"}:
        normalized = "fail"
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
        return panel(title, f"<p>{esc(section.get('text', ''))}</p>")
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
    parts = [f"<line x1='{pad}' y1='{height-pad}' x2='{width-pad}' y2='{height-pad}' stroke='#263440'/>"]
    for i, (label, value) in enumerate(zip(labels, values)):
        h = max(0.0, ((value - vmin) / span) * (height - 2 * pad))
        x = pad + i * (bar_width + gap)
        y = height - pad - h
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{h:.1f}' rx='3' fill='#67b7dc'/>")
        parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{height - 12}' fill='#9aa8b4' font-size='9' text-anchor='middle'>{esc(str(label)[:12])}</text>")
        parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{max(12, y - 5):.1f}' fill='#e6edf3' font-size='9' text-anchor='middle'>{value:.3g}</text>")
    target = spec.get("target_line")
    if isinstance(target, (int, float)) and vmax:
        ty = height - pad - ((float(target) - vmin) / span) * (height - 2 * pad)
        parts.append(f"<line x1='{pad}' y1='{ty:.1f}' x2='{width-pad}' y2='{ty:.1f}' stroke='#e2b15f' stroke-dasharray='5 4'/>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _line_svg(spec: dict) -> str:
    points = spec.get("points", [])
    width, height, pad = 420, 300, 38
    parts = [f"<rect x='{pad}' y='{pad}' width='{width-2*pad}' height='{height-2*pad}' fill='none' stroke='#263440'/>"]
    if spec.get("diagonal"):
        parts.append(f"<line x1='{pad}' y1='{height-pad}' x2='{width-pad}' y2='{pad}' stroke='#6f7f8e' stroke-dasharray='3 4'/>")
    coords = []
    for point in points:
        x, y = point.get("x"), point.get("y")
        if x is None or y is None:
            continue
        px = pad + float(x) * (width - 2 * pad)
        py = height - pad - float(y) * (height - 2 * pad)
        coords.append((px, py))
    if len(coords) > 1:
        parts.append("<polyline fill='none' stroke='#77d0a5' stroke-width='2' points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords) + "'/>")
    for x, y in coords:
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.2' fill='#67b7dc'/>")
    parts.append(f"<text x='{width/2:.0f}' y='{height-9}' fill='#9aa8b4' font-size='10' text-anchor='middle'>{esc(spec.get('x_label', 'x'))}</text>")
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
            parts.append(f"<line x1='{src[0]}' y1='{src[1]}' x2='{dst[0]}' y2='{dst[1]}' stroke='#263440'/>")
    for node in nodes:
        x, y = positions.get(node.get("id"), (0, 0))
        parts.append(f"<circle cx='{x}' cy='{y}' r='9' fill='#67b7dc'/>")
        parts.append(f"<text x='{x+15}' y='{y+4}' fill='#e6edf3' font-size='11'>{esc(node.get('label'))} <tspan fill='#9aa8b4'>{esc(node.get('short', ''))}</tspan></text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _timeline_svg(spec: dict) -> str:
    events = spec.get("events", [])
    width, height, pad = 760, 108, 34
    if not events:
        return '<div class="nv-subtitle">No timeline events available.</div>'
    step = (width - 2 * pad) / max(1, min(len(events), 80) - 1)
    parts = [f"<line x1='{pad}' y1='{height/2}' x2='{width-pad}' y2='{height/2}' stroke='#263440'/>"]
    for i, event in enumerate(events[:80]):
        x = pad + i * step
        parts.append(f"<circle cx='{x:.1f}' cy='{height/2}' r='4.2' fill='#77d0a5'/>")
        if i % 5 == 0:
            parts.append(f"<text x='{x:.1f}' y='{height/2-10:.1f}' fill='#9aa8b4' font-size='8' text-anchor='middle'>{esc(event.get('seq', i))}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


def _layout_svg(spec: dict) -> str:
    nodes = spec.get("nodes", [])
    width, height = 420, 300
    parts = []
    for node in nodes:
        x = float(node.get("x", .5)) * width
        y = float(node.get("y", .5)) * height
        color = "#67b7dc" if node.get("group") == "left" else "#77d0a5"
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='9' fill='{color}'/>")
        parts.append(f"<text x='{x:.1f}' y='{y-13:.1f}' fill='#e6edf3' font-size='10' text-anchor='middle'>{esc(node.get('label'))}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(parts)}</svg>"


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
        '<div class="nv-brand-sub">Clinical Intelligence Operating Environment</div></div>'
        f'<nav><div class="nv-nav">{nav_html}</div></nav></aside><main class="nv-main">'
        '<div class="nv-top"><div>'
        f'<h1 class="nv-page-title">{esc(title)}</h1><p class="nv-subtitle">{esc(subtitle)}</p>'
        f'</div><div class="nv-meta">{badge("backend", "v1")}{badge("version", version)}</div></div>'
        f'<div class="nv-grid">{flash}{sections}</div><div class="nv-footer">presentation layer only; platform truth remains in backend and registered artifacts</div>'
        '</main></div></body></html>'
    )


def _page_html(page: dict) -> str:
    content = "".join(render_section(section) for section in page.get("sections", []))
    content += "".join(render_visualization(viz) for viz in page.get("visualizations", []))
    content += render_controls(page.get("controls", []))
    return (
        f'<h2 class="nv-page-title">{esc(page.get("title"))}</h2>'
        f'<div class="nv-grid" style="margin-top:12px">{content}</div>'
    )


def render_workstation_view(view: Any, *, title: str, subtitle: str, version: str) -> str:
    data = view.to_dict() if hasattr(view, "to_dict") else view
    areas = data.get("areas", [])
    validation = data.get("validation", {})
    meta = data.get("meta", {})
    reveal = "".join(
        f"#tab-{esc(area.get('id'))}:checked ~ .nv-panels #area-{esc(area.get('id'))}{{display:block}}"
        f"#tab-{esc(area.get('id'))}:checked ~ .nv-tab-rail label[for='tab-{esc(area.get('id'))}']"
        "{background:rgba(103,183,220,.10);border-color:rgba(103,183,220,.34);color:var(--text)}"
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
        pagebar = "".join(f'<span class="nv-page-chip">{esc(page.get("title"))}</span>' for page in area.get("pages", []))
        pages = "".join(_page_html(page) for page in area.get("pages", []))
        panels.append(f'<section class="nv-area" id="area-{aid}"><div class="nv-pagebar">{pagebar}</div>{pages}</section>')
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
        f'<div class="nv-tabs">{"".join(radios)}<aside class="nv-tab-rail">'
        '<div class="nv-brand"><div class="nv-brand-title">NeuroVision</div>'
        f'<div class="nv-brand-sub">{esc(subtitle)}</div></div><nav class="nv-nav">{"".join(labels)}</nav></aside>'
        '<main class="nv-panels"><div class="nv-top"><div>'
        f'<h1 class="nv-page-title">{esc(title)}</h1><p class="nv-subtitle">{esc(subtitle)}. Every value originates from registered artifacts.</p>'
        f'</div><div class="nv-meta">{"".join(meta_badges)}</div></div>{"".join(panels)}'
        '<div class="nv-footer">deterministic static workstation; no backend truth is recomputed in the frontend</div>'
        '</main></div></body></html>'
    )


def render_research_view(view: Any, *, title: str, subtitle: str, version: str) -> str:
    data = view.to_dict() if hasattr(view, "to_dict") else view
    pages = data.get("pages", [])
    validation = data.get("validation", {})
    meta = data.get("meta", {})
    reveal = "".join(
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-panels #area-{esc(page.get('id'))}{{display:block}}"
        f"#tab-{esc(page.get('id'))}:checked ~ .nv-tab-rail label[for='tab-{esc(page.get('id'))}']"
        "{background:rgba(103,183,220,.10);border-color:rgba(103,183,220,.34);color:var(--text)}"
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
        f'<div class="nv-tabs">{"".join(radios)}<aside class="nv-tab-rail">'
        '<div class="nv-brand"><div class="nv-brand-title">NeuroVision</div>'
        f'<div class="nv-brand-sub">{esc(subtitle)}</div></div><nav class="nv-nav">{"".join(labels)}</nav></aside>'
        '<main class="nv-panels"><div class="nv-top"><div>'
        f'<h1 class="nv-page-title">{esc(title)}</h1><p class="nv-subtitle">{esc(subtitle)}. Registered artifacts are presented as a research workspace, not recomputed.</p>'
        f'</div><div class="nv-meta">{"".join(meta_badges)}</div></div>{"".join(panels)}'
        '<div class="nv-footer">offline deterministic research environment</div>'
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
