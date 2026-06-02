"""``backend/application_platform/reports`` — product report generation + export (T3-G).

Builds the deterministic product reports (Analysis / Prediction / Metadata / Model /
Evidence / Readiness / Audit / Lineage) and exports them in **JSON / HTML / PDF**. All
exporters are pure, stdlib-only, and deterministic (no wall-clock), so a given workflow
renders byte-identical reports across runs. The PDF is a minimal, valid, self-contained
PDF (a stdlib writer — no new dependency).
"""

from __future__ import annotations

import json

from ml.provenance import canonical_json, hash_obj

from ..version import APP_REPORT_VERSION


def _h(report_type: str) -> dict:
    return {"report_type": report_type, "app_report_version": APP_REPORT_VERSION}


# --- report builders ---------------------------------------------------------
def build_analysis_report(upload, analysis, prediction_result) -> dict:
    return {**_h("analysis"), "analysis": analysis.to_dict(), "upload": upload.to_dict(),
            "prediction": prediction_result.to_dict()}


def build_prediction_report(prediction_request, prediction_result) -> dict:
    return {**_h("prediction"), "prediction_request": prediction_request.to_dict(),
            "prediction_result": prediction_result.to_dict()}


def build_metadata_report(upload) -> dict:
    return {**_h("metadata"), "upload_id": upload.upload_id, "filename": upload.filename,
            "format": upload.fmt.value if upload.fmt else None,
            "sampling_frequency": upload.sampling_frequency, "n_channels": upload.n_channels,
            "duration_seconds": upload.duration_seconds,
            "analysis_seconds": upload.analysis_seconds}


def build_model_report(prediction_result) -> dict:
    return {**_h("model"), "model_id": prediction_result.model_id,
            "architecture": prediction_result.model_architecture,
            "readiness": prediction_result.model_readiness,
            "model_evidence": prediction_result.evidence.get("model", {})}


def build_evidence_report(prediction_result) -> dict:
    return {**_h("evidence"), "prediction_result_id": prediction_result.prediction_result_id,
            "evidence": prediction_result.evidence}


def build_readiness_report(readiness) -> dict:
    return {**_h("readiness"), "readiness": readiness.to_dict()}


def build_audit_report(audit_log, *, subject: str) -> dict:
    return {**_h("audit"), "subject": subject, "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(tracker, lineage_id) -> dict:
    chain = tracker.chain(lineage_id) if lineage_id else []
    return {**_h("lineage"), "lineage_id": lineage_id,
            "chain_verified": tracker.verify_chain(lineage_id) if lineage_id else False,
            "chain_length": len(chain), "chain_kinds": sorted({r.kind for r in chain}),
            "chain": [r.to_dict() for r in chain]}


# --- exporters (JSON / HTML / PDF) -------------------------------------------
def export_json(report: dict) -> str:
    return canonical_json(report)


def _escape(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _render_rows(obj, depth=0):
    """Render a nested dict/list as deterministic HTML definition rows."""
    out = []
    if isinstance(obj, dict):
        for k in sorted(obj):
            v = obj[k]
            if isinstance(v, (dict, list)):
                out.append(f'<div class="kv" style="margin-left:{depth*16}px">'
                           f'<span class="k">{_escape(k)}</span></div>')
                out.append("".join(_render_rows(v, depth + 1)))
            else:
                out.append(f'<div class="kv" style="margin-left:{depth*16}px">'
                           f'<span class="k">{_escape(k)}</span>: '
                           f'<span class="v">{_escape(v)}</span></div>')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                out.append("".join(_render_rows(v, depth + 1)))
            else:
                out.append(f'<div class="kv" style="margin-left:{depth*16}px">'
                           f'<span class="v">- {_escape(v)}</span></div>')
    else:
        out.append(f'<div class="kv">{_escape(obj)}</div>')
    return out


def export_html(report: dict) -> str:
    title = _escape(report.get("report_type", "report")).upper()
    body = "".join(_render_rows(report))
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>NeuroVision {title} Report</title>"
        "<style>body{font-family:system-ui,Arial,sans-serif;margin:24px;color:#1a1a1a}"
        "h1{font-size:18px;border-bottom:2px solid #2a6;padding-bottom:6px}"
        ".kv{font-size:13px;line-height:1.5}.k{font-weight:600;color:#246}"
        ".v{color:#333}</style></head><body>"
        f"<h1>NeuroVision &mdash; {title} Report</h1>"
        f"<div class='content'>{body}</div></body></html>"
    )


def export_pdf(report: dict) -> bytes:
    """Render the report as a minimal, valid, deterministic PDF (stdlib only)."""
    title = f"NeuroVision - {report.get('report_type', 'report').upper()} Report"
    lines = [title, ""]
    lines += _flatten_lines(report)

    def esc(s):
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    # build the text content stream (Helvetica 10pt, 14pt leading)
    content = ["BT", "/F1 10 Tf", "14 TL", "1 0 0 1 40 770 Tm"]
    for ln in lines[:55]:                       # one page, bounded
        content.append(f"({esc(ln[:110])}) Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objects)+1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF").encode()
    return bytes(pdf)


def _flatten_lines(obj, prefix="", depth=0):
    out = []
    pad = "  " * depth
    if isinstance(obj, dict):
        for k in sorted(obj):
            v = obj[k]
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out += _flatten_lines(v, prefix, depth + 1)
            else:
                out.append(f"{pad}{k}: {v}")
    elif isinstance(obj, list):
        for v in obj[:20]:
            if isinstance(v, (dict, list)):
                out += _flatten_lines(v, prefix, depth + 1)
            else:
                out.append(f"{pad}- {v}")
    else:
        out.append(f"{pad}{obj}")
    return out


def export(report: dict, fmt: str):
    fmt = fmt.lower()
    if fmt == "json":
        return export_json(report)
    if fmt == "html":
        return export_html(report)
    if fmt == "pdf":
        return export_pdf(report)
    raise ValueError(f"unsupported export format {fmt!r}")


def content_fingerprint(report: dict) -> str:
    return hash_obj({"json": json.loads(canonical_json(report))})


__all__ = [
    "build_analysis_report", "build_prediction_report", "build_metadata_report",
    "build_model_report", "build_evidence_report", "build_readiness_report", "build_audit_report",
    "build_lineage_report", "export_json", "export_html", "export_pdf", "export",
    "content_fingerprint",
]
