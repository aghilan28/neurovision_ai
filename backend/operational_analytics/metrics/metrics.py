"""Metrics engine (V3-P5).

Generates deterministic operational **metrics** across cases, reviews, findings,
knowledge, workflows, graphs, events and timelines: counts, rates, distributions,
durations, coverage, throughput, velocity, and health indicators. Every metric is
derived from the already-governed upstream artifacts (via the
:class:`AnalyticsSourceView`) and is explainable — it carries the inputs it
summarizes and a human-readable explanation.
"""

from __future__ import annotations

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_METRICS_ENGINE_VERSION
from . import _common as C

# Event categories that map to operational entity kinds (for counts/coverage).
_ENTITY_CATEGORIES = ("case", "review", "finding", "knowledge", "decision")


def _m(name, value, unit, observed, explanation, inputs=()):  # tiny constructor
    return AnalyticsMetric(name=name, value=float(value), unit=unit, observed=observed,
                           dimension="metrics", explanation=explanation, inputs=tuple(inputs))


class MetricsEngine:
    """Builds the ``metrics`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_METRICS_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        events = view.events()
        n_events = len(events)
        by_cat = view.event_counts_by_category()
        by_type = view.event_counts_by_type()
        workflows = view.workflows()

        # --- counts -----------------------------------------------------------
        metrics.append(_m("event_total", n_events, "count", n_events > 0,
                          "total operational events observed", ["event"]))
        metrics.append(_m("event_type_distinct", len(by_type), "count", bool(by_type),
                          "distinct event types observed", ["event"]))
        metrics.append(_m("workflow_total", len(workflows), "count", bool(workflows),
                          "total derived workflows", ["workflow"]))
        for cat in _ENTITY_CATEGORIES:
            metrics.append(_m(f"{cat}_event_count", by_cat.get(cat, 0), "count", cat in by_cat,
                              f"events in the {cat} category", ["event"]))

        # --- graph counts -----------------------------------------------------
        n_nodes = len(view.graph_node_ids())
        n_edges = len(view.graph_edge_ids())
        metrics.append(_m("graph_node_count", n_nodes, "count", view.has_graph(),
                          "nodes in the operational graph", ["graph_node"]))
        metrics.append(_m("graph_edge_count", n_edges, "count", view.has_graph(),
                          "edges in the operational graph", ["graph_edge"]))

        # --- rates / distributions -------------------------------------------
        # event category distribution as a ratio of total
        for cat in _ENTITY_CATEGORIES:
            metrics.append(_m(f"{cat}_event_rate", C.safe_ratio_0_1(by_cat.get(cat, 0), n_events),
                              "ratio", n_events > 0,
                              f"fraction of events in the {cat} category", ["event"]))

        # --- throughput / velocity (from workflows) --------------------------
        throughputs = [w.metric("throughput").value for w in workflows
                       if w.metric("throughput") is not None]
        velocities = [w.metric("operational_velocity").value for w in workflows
                      if w.metric("operational_velocity") is not None]
        metrics.append(_m("mean_throughput", C.mean(throughputs), "ratio", bool(throughputs),
                          "mean workflow throughput (transitions per event)", ["workflow"]))
        metrics.append(_m("mean_operational_velocity", C.mean(velocities), "ratio",
                          bool(velocities),
                          "mean workflow velocity (transitions per logical-step span)",
                          ["workflow"]))

        # --- durations (from temporal analytics, logical steps) --------------
        if view.has_temporal():
            for dm in view.temporal_analytics().metrics:
                if dm.name.endswith("_steps") or dm.name.endswith("_count") or dm.name.endswith("_total"):
                    metrics.append(_m(f"temporal_{dm.name}", dm.steps if dm.observed else
                                      C.SENTINEL_UNOBSERVED, "logical_steps", dm.observed,
                                      f"temporal: {dm.detail}", ["temporal_analytics"]))

        # --- coverage ---------------------------------------------------------
        # fraction of workflows that reached a completed terminal state
        completed = [w for w in workflows
                     if (w.metric("completion_rate") and w.metric("completion_rate").value >= 1.0)]
        metrics.append(_m("workflow_completion_coverage",
                          C.safe_ratio_0_1(len(completed), len(workflows)), "ratio",
                          bool(workflows),
                          "fraction of workflows reaching a completed state", ["workflow"]))

        return metrics
