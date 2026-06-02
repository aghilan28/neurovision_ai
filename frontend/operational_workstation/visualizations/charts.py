"""Deterministic chart-spec builders for the operational workstation (V3-P7).

Each returns a ``Visualization`` whose ``spec`` is a plain, JSON-able dict. No
randomness, no recomputation of domain values — they only reshape registered
snapshot data for display (the ten mandated visualization families).
"""

from __future__ import annotations

from ..schemas import Visualization


def _short(lid: str) -> str:
    return str(lid).split("+")[-1][:8]


# --- 1. event streams ---------------------------------------------------------
def event_stream(events: list, *, limit: int = 60) -> Visualization:
    """An ordered timeline of operational events (by category)."""
    points = [{"seq": i, "kind": e.get("event_type"), "category": e.get("category"),
               "hash": _short(e.get("event_id", ""))}
              for i, e in enumerate(events[:limit])]
    return Visualization("timeline", "Event Stream", {"events": points, "n": len(events)})


def event_category_distribution(registry: dict) -> Visualization:
    """Bar chart of event counts by category (from the event registry)."""
    by_cat = registry.get("by_category", {})
    if not by_cat:
        counts: dict = {}
        for rec in registry.get("events", {}).values():
            c = rec.get("category", "?")
            counts[c] = counts.get(c, 0) + 1
        by_cat = counts
    labels = sorted(by_cat)
    return Visualization("bar", "Event Categories",
                         {"labels": labels, "values": [by_cat[k] for k in labels]})


# --- 2. timeline evolution ----------------------------------------------------
def timeline_evolution(evolution_artifact: dict) -> Visualization:
    """Ordered state transitions of a subject as a left-to-right graph."""
    steps = evolution_artifact.get("steps", [])
    nodes, edges = [], []
    prev_id = None
    for i, s in enumerate(steps):
        nid = f"s{i}"
        label = s.get("to_state") or s.get("state") or s.get("event_type") or "?"
        nodes.append({"id": nid, "label": label, "short": str(i)})
        if prev_id is not None:
            edges.append({"from": prev_id, "to": nid})
        prev_id = nid
    return Visualization("graph", "Timeline Evolution", {"nodes": nodes, "edges": edges})


# --- 3. workflow flows --------------------------------------------------------
def workflow_flow(workflow: dict) -> Visualization:
    """A single workflow's transitions rendered as an ordered flow graph."""
    reports = workflow.get("reports", {})
    transitions = reports.get("transition_report", {}).get("transitions", [])
    nodes, edges, seen = [], [], {}

    def _node(state):
        if state not in seen:
            seen[state] = f"n{len(seen)}"
            nodes.append({"id": seen[state], "label": state, "short": ""})
        return seen[state]

    for t in transitions:
        a = _node(t.get("from_state", "?"))
        b = _node(t.get("to_state", "?"))
        edges.append({"from": a, "to": b})
    return Visualization("graph", f"Workflow Flow ({workflow.get('subject_id', '')[:14]})",
                         {"nodes": nodes, "edges": edges})


# --- 4. dependency networks ---------------------------------------------------
def dependency_network(workflow: dict) -> Visualization:
    """Workflow dependency relations as a network graph."""
    deps = workflow.get("reports", {}).get("dependency_report", {}).get("dependencies", [])
    nodes, edges, seen = [], [], set()

    def _add(nid, label):
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "short": _short(nid)})

    for d in deps:
        src = d.get("source_id") or d.get("entity_id") or "?"
        dst = d.get("target_id") or d.get("depends_on") or d.get("related_id") or src
        _add(src, d.get("entity_kind", "entity"))
        _add(dst, d.get("relation", "rel"))
        edges.append({"from": src, "to": dst, "label": d.get("relation", "")})
    return Visualization("graph", "Dependency Network", {"nodes": nodes, "edges": edges})



# --- 5. graph structures ------------------------------------------------------
def graph_structure(graph_registry: dict, *, limit: int = 60) -> Visualization:
    """Operational graph nodes + edges (capped for display)."""
    nodes_d = graph_registry.get("nodes", {})
    edges_d = graph_registry.get("edges", {})
    items = list(nodes_d.items())[:limit]
    keep = {nid for nid, _ in items}
    nodes = [{"id": nid, "label": n.get("node_type", "?"), "short": _short(n.get("source_id", nid))}
             for nid, n in items]
    edges = []
    for e in edges_d.values():
        if e.get("source_node") in keep and e.get("target_node") in keep:
            edges.append({"from": e["source_node"], "to": e["target_node"],
                          "label": e.get("edge_type", "")})
    return Visualization("graph", "Operational Graph Structure",
                         {"nodes": nodes, "edges": edges,
                          "total_nodes": graph_registry.get("n_nodes"),
                          "total_edges": graph_registry.get("n_edges")})


# --- 6. analytics trends ------------------------------------------------------
def analytics_metrics(analytics_artifact: dict, *, title: str = "Analytics Metrics") -> Visualization:
    """Bounded bar chart of an analytics record's observed metrics."""
    metrics = [m for m in analytics_artifact.get("metrics", [])
               if m.get("observed") and m.get("unit") in ("ratio", "score")]
    return Visualization("bar", title,
                         {"labels": [m.get("name") for m in metrics],
                          "values": [round(float(m.get("value", 0.0)), 4) for m in metrics],
                          "max": 1.0})


def trend_indices(trend_artifact: dict) -> Visualization:
    """Trend indices in [-1, 1] rendered as a signed bar chart."""
    metrics = [m for m in trend_artifact.get("metrics", []) if m.get("unit") == "index"]
    return Visualization("bar", "Analytics Trends (signed index)",
                         {"labels": [m.get("name") for m in metrics],
                          "values": [round(float(m.get("value", 0.0)), 4) for m in metrics],
                          "max": 1.0, "min": -1.0})


# --- 7. risk trends -----------------------------------------------------------
def risk_scores(risk_artifact: dict) -> Visualization:
    """Risk scores in [0, 1] as a bounded bar chart (higher = more risk)."""
    metrics = [m for m in risk_artifact.get("metrics", []) if m.get("dimension") == "risk"]
    return Visualization("bar", "Operational Risk Scores",
                         {"labels": [m.get("name") for m in metrics],
                          "values": [round(float(m.get("value", 0.0)), 4) for m in metrics],
                          "max": 1.0})


# --- 8. recommendation priorities --------------------------------------------
def recommendation_priorities(recommendations: list) -> Visualization:
    """Count of recommendations by priority level (low..critical)."""
    order = ["low", "medium", "high", "critical"]
    counts = {lvl: 0 for lvl in order}
    for r in recommendations:
        lvl = r.get("priority", {}).get("level", "low")
        counts[lvl] = counts.get(lvl, 0) + 1
    return Visualization("bar", "Recommendation Priorities",
                         {"labels": order, "values": [counts[lvl] for lvl in order]})


# --- 9. audit timelines -------------------------------------------------------
def audit_timeline(events: list, *, title: str = "Audit Timeline") -> Visualization:
    """An ordered timeline of immutable audit events."""
    points = [{"seq": e.get("seq"), "kind": e.get("kind"),
               "hash": _short(e.get("event_hash", ""))} for e in events]
    return Visualization("timeline", title, {"events": points, "n": len(points)})


def version_history(records: list) -> Visualization:
    """A table of version-change audit events (version lineage of artifacts)."""
    rows = []
    for e in records:
        if e.get("kind") == "version_changed":
            payload = e.get("payload", {})
            rows.append([e.get("seq"), _short(payload.get("version", "")),
                         payload.get("reason", "")])
    return Visualization("table", "Version History",
                         {"rows": rows, "headers": ["seq", "version", "reason"]})


# --- 10. lineage graphs -------------------------------------------------------
def lineage_graph(lineage: dict, *, limit: int = 60) -> Visualization:
    """Nodes = lineage records (by kind); edges = parent links (capped for display)."""
    records = lineage.get("records", {})
    items = list(records.items())[:limit]
    keep = {lid for lid, _ in items}
    nodes, edges = [], []
    for lid, rec in items:
        nodes.append({"id": lid, "label": rec.get("kind", "?"), "short": _short(lid)})
        for parent in rec.get("parents", []):
            if parent in keep:
                edges.append({"from": parent, "to": lid})
    return Visualization("graph", "Lineage Graph",
                         {"nodes": nodes, "edges": edges, "total_records": lineage.get("n_records")})


def traceability_graph(chain_records: list) -> Visualization:
    """The representative Patient -> Recommendation chain as a graph."""
    nodes, edges = [], []
    keep = {r["lineage_id"] for r in chain_records}
    for rec in chain_records:
        nodes.append({"id": rec["lineage_id"], "label": rec.get("kind", "?"),
                      "short": _short(rec["lineage_id"])})
        for parent in rec.get("parents", []):
            if parent in keep:
                edges.append({"from": parent, "to": rec["lineage_id"]})
    return Visualization("graph", "Traceability (Patient -> Recommendation)",
                         {"nodes": nodes, "edges": edges})
