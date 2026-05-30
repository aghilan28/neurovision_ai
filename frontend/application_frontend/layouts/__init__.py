"""``frontend/application_frontend/layouts`` — deterministic static HTML rendering.

Turns a Page view-model dict into a complete, **deterministic** HTML document: inline
CSS only, no JavaScript, no external assets (mirrors every prior NeuroVision frontend).
The same Page dict always renders byte-identical HTML. All dynamic values are
HTML-escaped.
"""

from __future__ import annotations

from ..util import esc
from ..version import APPLICATION_FRONTEND_VERSION

_CSS = """
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
color:#1c2530;background:#f4f6f9}header{background:#0f2740;color:#fff;padding:14px 22px}
header h1{margin:0;font-size:18px;font-weight:600}nav{background:#143553;display:flex;flex-wrap:wrap}
nav a{color:#cfe0f0;text-decoration:none;padding:11px 16px;font-size:14px}
nav a.active{background:#1f4a73;color:#fff;font-weight:600}main{max-width:980px;margin:0 auto;padding:22px}
h2.sub{font-size:14px;font-weight:400;color:#5a6b7b;margin:4px 0 0}
section.card{background:#fff;border:1px solid #dfe5ec;border-radius:8px;padding:16px 18px;margin:0 0 16px}
section.card h3{margin:0 0 12px;font-size:15px;color:#0f2740;border-bottom:1px solid #eef2f6;padding-bottom:8px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 9px;border-bottom:1px solid #eef2f6}
th{color:#5a6b7b;font-weight:600;background:#f8fafc}.kv{display:grid;grid-template-columns:230px 1fr;gap:6px 14px;font-size:13px}
.kv dt{color:#5a6b7b}.kv dd{margin:0;font-family:ui-monospace,Menlo,Consolas,monospace;word-break:break-all}
.alert{padding:11px 14px;border-radius:6px;font-size:14px;margin:0 0 16px}
.alert.info{background:#e7f1fb;color:#0f3c66}.alert.success{background:#e6f6ec;color:#1c6b3a}
.alert.warning{background:#fdf3e1;color:#8a5a12}.alert.error{background:#fce8e8;color:#8a1f1f}
form{display:grid;gap:12px;max-width:460px}label{font-size:13px;color:#33414f;display:grid;gap:5px}
input,select{padding:9px 10px;border:1px solid #c6cfd9;border-radius:6px;font-size:14px}
button{background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:10px 16px;font-size:14px;cursor:pointer;width:max-content}
.err{color:#8a1f1f;font-size:12px}.steps{display:flex;flex-wrap:wrap;gap:8px;list-style:none;padding:0;margin:0}
.steps li{padding:7px 12px;border-radius:16px;font-size:12px;background:#eef2f6;color:#5a6b7b}
.steps li.done{background:#e6f6ec;color:#1c6b3a;font-weight:600}
pre{background:#0f1b2a;color:#d6e2f0;padding:12px;border-radius:6px;overflow:auto;font-size:12px;max-height:340px}
ul.items{margin:0;padding-left:18px;font-size:13px}footer{color:#8a97a5;font-size:12px;text-align:center;padding:18px}
"""


def _render_section(s: dict) -> str:
    t = s.get("type")
    if t == "alert":
        return f'<div class="alert {esc(s["level"])}">{esc(s["message"])}</div>'
    head = f'<h3>{esc(s["heading"])}</h3>' if s.get("heading") else ""
    if t == "kv":
        rows = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in s["rows"])
        return f'<section class="card">{head}<dl class="kv">{rows}</dl></section>'
    if t == "table":
        cols = "".join(f"<th>{esc(c)}</th>" for c in s["columns"])
        body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>"
                       for row in s["rows"])
        return f'<section class="card">{head}<table><thead><tr>{cols}</tr></thead><tbody>{body}</tbody></table></section>'
    if t == "form":
        return _render_form(s, head)
    if t == "stages":
        lis = "".join(f'<li class="{"done" if st["done"] else ""}">{esc(st["stage"])}</li>'
                      for st in s["stages"])
        return f'<section class="card">{head}<ul class="steps">{lis}</ul></section>'
    if t == "list":
        lis = "".join(f"<li>{esc(i)}</li>" for i in s["items"]) or "<li>—</li>"
        return f'<section class="card">{head}<ul class="items">{lis}</ul></section>'
    if t == "report":
        return f'<section class="card">{head}<pre>{esc(s["json"])}</pre></section>'
    if t == "prose":
        return f'<section class="card">{head}<p>{esc(s["text"])}</p></section>'
    return ""


def _render_form(s: dict, head: str) -> str:
    form = s["form"]
    errs = {e["field"]: e["message"] for e in s.get("field_errors", [])}
    rows = []
    for fld in form["fields"]:
        err = f'<span class="err">{esc(errs[fld["name"]])}</span>' if fld["name"] in errs else ""
        if fld["kind"] == "select":
            opts = "".join(f'<option value="{esc(o)}">{esc(o)}</option>' for o in fld["options"])
            ctrl = f'<select name="{esc(fld["name"])}">{opts}</select>'
        elif fld["kind"] == "file":
            ctrl = f'<input type="file" name="{esc(fld["name"])}">'
        else:
            kind = "password" if fld["kind"] == "password" else "text"
            ph = f' placeholder="{esc(fld["placeholder"])}"' if fld.get("placeholder") else ""
            ctrl = f'<input type="{kind}" name="{esc(fld["name"])}"{ph}>'
        rows.append(f'<label>{esc(fld["label"])}{ctrl}{err}</label>')
    fields_html = "".join(rows)
    return (f'<section class="card">{head}'
            f'<form method="{esc(form["method"])}" data-action="{esc(form["action"])}">'
            f'{fields_html}<button type="submit">{esc(form["submit_label"])}</button></form></section>')


def render(page: dict) -> str:
    """Render a Page dict into a complete, deterministic HTML document."""
    nav = "".join(
        f'<a class="{"active" if i.get("active") else ""}" href="#{esc(i["id"])}">{esc(i["label"])}</a>'
        for i in page.get("nav", []))
    flash = ""
    if page.get("flash"):
        flash = (f'<div class="alert {esc(page["flash"].get("level") or "info")}">'
                 f'{esc(page["flash"].get("message"))}</div>')
    sections = "".join(_render_section(s) for s in page.get("sections", []))
    subtitle = f'<h2 class="sub">{esc(page["subtitle"])}</h2>' if page.get("subtitle") else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(page.get('title', 'NeuroVision'))}</title><style>{_CSS}</style></head><body>"
        f'<header><h1>NeuroVision AI</h1></header><nav>{nav}</nav>'
        f'<main><h2 style="margin:0 0 2px">{esc(page.get("title", ""))}</h2>{subtitle}'
        f'<div style="margin-top:16px">{flash}{sections}</div></main>'
        f'<footer>{esc(APPLICATION_FRONTEND_VERSION)} · presentation layer · backend API v1</footer>'
        "</body></html>")


__all__ = ["render"]
