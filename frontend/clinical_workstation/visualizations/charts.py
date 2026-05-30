"""Deterministic chart-spec builders for the workstation.

Each returns a ``Visualization`` whose ``spec`` is a plain, JSON-able dict. No
randomness, no recomputation of domain values — they only reshape registered
snapshot data for display (the ten mandated visualization families plus an
audit timeline).
"""

from __future__ import annotations

from ..schemas import Visualization


def _short(lid: str) -> str:
    return str(lid).split("+")[-1][:8]


# --- lifecycle / status visualizations ---------------------------------------
def case_lifecycle(cases: list) -> Visualization:
    """Distribution of case statuses across the population."""
    counts: dict = {}
    for c in cases:
        status = c.get("registry_record", {}).get("status", "?")
        counts[status] = counts.get(status, 0) + 1
    labels = sorted(counts)
    return Visualization("bar", "Case Lifecycle (status distribution)",
                         {"labels": labels, "values": [counts[k] for k in labels]})


def review_lifecycle(reviews: list) -> Visualization:
    counts: dict = {}
    for r in reviews:
        status = r.get("registry_record", {}).get("status", "?")
        counts[status] = counts.get(status, 0) + 1
    labels = sorted(counts)
    return Visualization("bar", "Review Lifecycle (status distribution)",
                         {"labels": labels, "values": [counts[k] for k in labels]})


def finding_lifecycle(findings: list) -> Visualization:
    counts: dict = {}
    for f in findings:
        status = f.get("registry_record", {}).get("status", "?")
        counts[status] = counts.get(status, 0) + 1
    labels = sorted(counts)
    return Visualization("bar", "Finding Lifecycle (status distribution)",
                         {"labels": labels, "values": [counts[k] for k in labels]})


# --- knowledge ----------------------------------------------------------------
def knowledge_relationships(relationships: dict) -> Visualization:
    """Graph of knowledge relationships (nodes = endpoints, edges = relations)."""
    nodes: dict = {}
    edges = []
    for rid, rec in relationships.get("relations", {}).items():
        src = rec.get("source_id") or rec.get("from") or rec.get("subject")
        dst = rec.get("target_id") or rec.get("to") or rec.get("object")
        rel = rec.get("relation") or rec.get("predicate") or rec.get("kind", "rel")
        if src:
            nodes[src] = {"id": src, "label": "concept", "short": _short(src)}
        if dst:
            nodes[dst] = {"id": dst, "label": "concept", "short": _short(dst)}
        if src and dst:
            edges.append({"from": src, "to": dst, "label": rel})
    return Visualization("graph", "Knowledge Relationships",
                         {"nodes": list(nodes.values()), "edges": edges})


# --- intelligence -------------------------------------------------------------
def population_analytics(analytics_artifact: dict) -> Visualization:
    """Population counts by subject kind (from the analytics blocks)."""
    blocks = analytics_artifact.get("blocks", [])
    labels = [b.get("subject_kind", "?") for b in blocks]
    values = [b.get("count", 0) for b in blocks]
    return Visualization("bar", "Population Analytics (counts by kind)",
                         {"labels": labels, "values": values})


def trend_analysis(trend_artifact: dict, metric: str = "finding_status_progression") -> Visualization:
    """A single trend series rendered as a line over its ordinal buckets."""
    series = None
    for s in trend_artifact.get("series", []):
        if s.get("metric") == metric:
            series = s
            break
    if series is None and trend_artifact.get("series"):
        series = trend_artifact["series"][0]
    points = []
    pts = (series or {}).get("points", [])
    n = max(1, len(pts) - 1)
    for i, p in enumerate(pts):
        points.append({"x": round(i / n, 4), "y": p.get("value", 0), "label": p.get("bucket")})
    return Visualization("line", f"Trend: {(series or {}).get('metric', metric)}",
                         {"points": points, "x_label": "stage", "y_label": "value",
                          "direction": (series or {}).get("direction")})


def quality_metrics(quality_artifact: dict) -> Visualization:
    metrics = quality_artifact.get("metrics", [])
    return Visualization("bar", "Quality Metrics",
                         {"labels": [m.get("name") for m in metrics],
                          "values": [round(float(m.get("value", 0.0)), 4) for m in metrics],
                          "max": 1.0})


# --- decision support ---------------------------------------------------------
def decision_context(risk_artifact: dict) -> Visualization:
    """Risk components of a decision context as a bounded bar chart."""
    comps = risk_artifact.get("components", [])
    return Visualization("bar", "Decision Risk Context (components)",
                         {"labels": [c.get("name") for c in comps],
                          "values": [round(float(c.get("value", 0.0)), 4) for c in comps],
                          "max": 1.0, "aggregate": risk_artifact.get("aggregate"),
                          "band": risk_artifact.get("band")})


# --- lineage / audit / version ------------------------------------------------
def lineage_graph(lineage: dict, *, limit: int = 60) -> Visualization:
    """Nodes = lineage records (by kind); edges = parent links (capped for display)."""
    records = lineage.get("records", {})
    items = list(records.items())[:limit]
    nodes, edges = [], []
    keep = {lid for lid, _ in items}
    for lid, rec in items:
        nodes.append({"id": lid, "label": rec.get("kind", "?"), "short": _short(lid)})
        for parent in rec.get("parents", []):
            if parent in keep:
                edges.append({"from": parent, "to": lid})
    return Visualization("graph", "Lineage Graph", {"nodes": nodes, "edges": edges,
                                                    "total_records": lineage.get("n_records")})


def traceability_graph(chain_records: list) -> Visualization:
    """The representative Patient -> Decision Support chain as a graph."""
    nodes, edges = [], []
    keep = {r["lineage_id"] for r in chain_records}
    for rec in chain_records:
        nodes.append({"id": rec["lineage_id"], "label": rec.get("kind", "?"),
                      "short": _short(rec["lineage_id"])})
        for parent in rec.get("parents", []):
            if parent in keep:
                edges.append({"from": parent, "to": rec["lineage_id"]})
    return Visualization("graph", "Traceability (Patient -> Decision Support)",
                         {"nodes": nodes, "edges": edges})


def audit_timeline(events: list, *, title: str = "Audit Timeline") -> Visualization:
    """An ordered timeline of immutable audit events."""
    points = [{"seq": e.get("seq"), "kind": e.get("kind"),
               "hash": _short(e.get("event_hash", ""))} for e in events]
    return Visualization("timeline", title, {"events": points, "n": len(points)})


def version_history(records: list) -> Visualization:
    """A table of version-change audit events (version lineage of an artifact)."""
    rows = []
    for e in records:
        if e.get("kind") == "version_changed":
            payload = e.get("payload", {})
            rows.append([e.get("seq"), _short(payload.get("version", "")), payload.get("reason", "")])
    return Visualization("table", "Version History",
                         {"rows": rows, "headers": ["seq", "version", "reason"]})
