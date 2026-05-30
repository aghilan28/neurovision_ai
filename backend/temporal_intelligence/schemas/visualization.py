"""Temporal visualization-ready contracts (V3-P2).

Contracts only — **no UI implementation**. Each builder turns a temporal artifact
into a JSON-able :class:`VisualizationContract` that a future presentation layer
(e.g. the Clinical Workstation) can render without importing any domain module.
Supported families: timeline, event_sequence, evolution_graph, duration_graph,
trend_graph, operational_dashboard.
"""

from __future__ import annotations


from ..models.domain import VisualizationContract


def timeline_contract(timeline) -> VisualizationContract:
    t = timeline.to_dict() if hasattr(timeline, "to_dict") else timeline
    points = [{"order": p["order"], "label": p["event_type"], "category": p["category"],
               "event_id": p["event_id"]} for p in t["points"]]
    return VisualizationContract("timeline", f"Timeline {t['scope']}",
                                 {"subject_kind": t["subject_kind"], "subject_id": t["subject_id"],
                                  "points": points})


def event_sequence_contract(timeline) -> VisualizationContract:
    t = timeline.to_dict() if hasattr(timeline, "to_dict") else timeline
    seq = [p["event_type"] for p in t["points"]]
    edges = [{"from": i, "to": i + 1} for i in range(len(seq) - 1)]
    return VisualizationContract("event_sequence", f"Event Sequence {t['scope']}",
                                 {"sequence": seq, "edges": edges})


def evolution_graph_contract(evolution) -> VisualizationContract:
    e = evolution.to_dict() if hasattr(evolution, "to_dict") else evolution
    nodes, edges = [], []
    for s in e["steps"]:
        nodes.append({"state": s["to_state"], "order": s["order"]})
        if s["from_state"] is not None:
            edges.append({"from": s["from_state"], "to": s["to_state"],
                          "event_type": s["event_type"]})
    return VisualizationContract("evolution_graph", f"Evolution {e['scope']}",
                                 {"nodes": nodes, "edges": edges})


def duration_graph_contract(analytics) -> VisualizationContract:
    a = analytics.to_dict() if hasattr(analytics, "to_dict") else analytics
    bars = [{"label": m["name"], "value": m["steps"], "observed": m["observed"]}
            for m in a["metrics"]]
    return VisualizationContract("duration_graph", f"Durations {a['scope']}",
                                 {"unit": "logical_steps", "bars": bars})


def trend_graph_contract(analytics) -> VisualizationContract:
    a = analytics.to_dict() if hasattr(analytics, "to_dict") else analytics
    counts = a.get("counts", {})
    points = [{"label": k, "value": v} for k, v in sorted(counts.items())]
    return VisualizationContract("trend_graph", f"Event-type counts {a['scope']}",
                                 {"points": points})


def operational_dashboard_contract(timeline, analytics) -> VisualizationContract:
    t = timeline.to_dict() if hasattr(timeline, "to_dict") else timeline
    a = analytics.to_dict() if hasattr(analytics, "to_dict") else analytics
    return VisualizationContract(
        "operational_dashboard", "Operational Dashboard (contract)",
        {"timeline_length": t["length"],
         "event_type_counts": a.get("counts", {}),
         "duration_metrics": {m["name"]: m["steps"] for m in a["metrics"]},
         "note": "contract only; no UI implementation (V3-P2)"})


def all_contracts(*, timeline, evolution, analytics) -> list:
    return [
        timeline_contract(timeline).to_dict(),
        event_sequence_contract(timeline).to_dict(),
        evolution_graph_contract(evolution).to_dict(),
        duration_graph_contract(analytics).to_dict(),
        trend_graph_contract(analytics).to_dict(),
        operational_dashboard_contract(timeline, analytics).to_dict(),
    ]
