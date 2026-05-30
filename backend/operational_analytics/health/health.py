"""Health engine (V3-P5).

Generates explainable **health scores** for cases, reviews, workflows, knowledge,
the graph, and overall operational/system health. Every health score is a bounded
[0, 1] composite of derived sub-signals, and every score carries an explanation of
the signals that produced it — health calculations must be explainable.

All inputs come from the already-derived workflow metrics and event/graph counts
(via the :class:`AnalyticsSourceView`); nothing is invented.
"""

from __future__ import annotations

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_HEALTH_ENGINE_VERSION
from ..metrics import _common as C


def _h(name, value, observed, explanation, inputs=()):
    return AnalyticsMetric(name=name, value=float(value), unit="score", observed=observed,
                           dimension="health", explanation=explanation, inputs=tuple(inputs))


class HealthEngine:
    """Builds the ``health`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_HEALTH_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        workflows = view.workflows()

        # --- workflow health (mean of the workflows' own health scores) ------
        wf_health = [w.metric("workflow_health_score").value for w in workflows
                     if w.metric("workflow_health_score") is not None]
        workflow_health = C.mean(wf_health)
        metrics.append(_h("workflow_health", workflow_health, bool(wf_health),
                          "mean of derived per-workflow health scores", ["workflow"]))

        # --- case health (completion minus rework penalty) -------------------
        case_wfs = [w for w in workflows if w.subject_kind == "case"]
        case_completion = C.mean([w.metric("completion_rate").value for w in case_wfs
                                  if w.metric("completion_rate") is not None])
        case_rework = C.mean([w.metric("rework_rate").value for w in case_wfs
                              if w.metric("rework_rate") is not None])
        case_health = C.clamp01(0.7 * case_completion + 0.3 * (1.0 - case_rework))
        metrics.append(_h("case_health", case_health, bool(case_wfs),
                          "0.7*completion + 0.3*(1-rework) over case workflows", ["workflow"]))

        # --- review health (review-category events vs reopen signal) ---------
        by_type = view.event_counts_by_type()
        reviews_completed = by_type.get("REVIEW_COMPLETED", 0)
        reviews_reopened = by_type.get("REVIEW_REOPENED", 0)
        reviews_started = by_type.get("REVIEW_STARTED", 0)
        review_health = C.clamp01(
            C.safe_ratio_0_1(reviews_completed, max(1, reviews_started))
            - C.safe_ratio_0_1(reviews_reopened, max(1, reviews_started)))
        metrics.append(_h("review_health", review_health,
                          reviews_started > 0,
                          "completion rate minus reopen rate over started reviews", ["event"]))

        # --- knowledge health (knowledge activity present + linked) ----------
        knowledge_events = sum(v for k, v in by_type.items() if k.startswith("KNOWLEDGE_"))
        knowledge_health = 1.0 if knowledge_events > 0 else 0.0
        metrics.append(_h("knowledge_health", knowledge_health, knowledge_events > 0,
                          "knowledge base shows recorded activity", ["event"]))

        # --- graph health (connectivity: edges per node, capped) -------------
        n_nodes = len(view.graph_node_ids())
        n_edges = len(view.graph_edge_ids())
        graph_health = C.clamp01(C.ratio(n_edges, n_nodes)) if n_nodes else 0.0
        metrics.append(_h("graph_health", graph_health, view.has_graph(),
                          "graph connectivity (edges per node, capped at 1.0)",
                          ["graph_node", "graph_edge"]))

        # --- stall penalty (workflows flagged stalled / rework) --------------
        stalled = sum(1 for w in workflows if "workflow_stall" in w.metadata.bottlenecks)
        rework = sum(1 for w in workflows if "repeated_rework" in w.metadata.bottlenecks)
        stall_penalty = C.safe_ratio_0_1(stalled + rework, max(1, len(workflows)))
        metrics.append(_h("stall_penalty", stall_penalty, bool(workflows),
                          "fraction of workflows showing stall/rework bottlenecks",
                          ["workflow"]))

        # --- operational health (composite) ----------------------------------
        components = [m.value for m in metrics if m.name in (
            "workflow_health", "case_health", "review_health", "knowledge_health", "graph_health")
            and m.observed]
        operational_health = C.clamp01(C.mean(components) - 0.2 * stall_penalty) if components else 0.0
        metrics.append(_h("operational_health", operational_health, bool(components),
                          "mean of observed health signals minus stall penalty",
                          ["workflow", "event", "graph_node"]))

        # --- system health score (operational health gated by data presence) -
        has_data = len(view.events()) > 0
        system_health = operational_health if has_data else 0.0
        metrics.append(_h("system_health_score", system_health, has_data,
                          "operational health, valid only when operational data exists",
                          ["event", "workflow", "graph_node"]))

        return metrics
