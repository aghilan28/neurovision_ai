"""Quality engine (V3-P5).

Analyzes **operational quality**: workflow quality, review quality, finding
quality, knowledge quality, graph integrity, and analytics integrity. Each quality
metric is a bounded [0, 1] score derived from already-governed artifacts and is
explainable. Quality analytics never mutate the artifacts they inspect.
"""

from __future__ import annotations

from ..models.domain import AnalyticsMetric
from ..models.source import AnalyticsSourceView
from ..version import ANALYTICS_QUALITY_ENGINE_VERSION
from ..metrics import _common as C


def _q(name, value, unit, observed, explanation, inputs=()):
    return AnalyticsMetric(name=name, value=float(value), unit=unit, observed=observed,
                           dimension="quality", explanation=explanation, inputs=tuple(inputs))


class QualityEngine:
    """Builds the ``quality`` analytics dimension (read-only, deterministic)."""

    engine_version = ANALYTICS_QUALITY_ENGINE_VERSION

    def compute(self, view: AnalyticsSourceView) -> list[AnalyticsMetric]:
        metrics: list[AnalyticsMetric] = []
        workflows = view.workflows()
        by_type = view.event_counts_by_type()

        # --- workflow quality (low rework + low slow transitions) ------------
        rework = C.mean([w.metric("rework_rate").value for w in workflows
                         if w.metric("rework_rate") is not None])
        n_bottlenecked = sum(1 for w in workflows if w.metadata.bottlenecks)
        bottleneck_rate = C.safe_ratio_0_1(n_bottlenecked, max(1, len(workflows)))
        workflow_quality = C.clamp01(1.0 - 0.5 * rework - 0.5 * bottleneck_rate)
        metrics.append(_q("workflow_quality", workflow_quality, "score", bool(workflows),
                          "1 - 0.5*rework - 0.5*bottleneck_rate over workflows", ["workflow"]))

        # --- review quality (confirmed/finalized vs reopened) ----------------
        completed = by_type.get("REVIEW_COMPLETED", 0)
        reopened = by_type.get("REVIEW_REOPENED", 0)
        review_quality = C.clamp01(C.safe_ratio_0_1(completed, max(1, completed + reopened)))
        metrics.append(_q("review_quality", review_quality, "ratio", (completed + reopened) > 0,
                          "completed / (completed + reopened) reviews", ["event"]))

        # --- finding quality (confirmed vs superseded/revised) ---------------
        confirmed = by_type.get("FINDING_CONFIRMED", 0)
        revised = by_type.get("FINDING_REVISED", 0)
        superseded = by_type.get("FINDING_SUPERSEDED", 0)
        denom = confirmed + revised + superseded
        finding_quality = C.clamp01(C.safe_ratio_0_1(confirmed, max(1, denom)))
        metrics.append(_q("finding_quality", finding_quality, "ratio", denom > 0,
                          "confirmed / (confirmed + revised + superseded) findings", ["event"]))

        # --- knowledge quality (linked evidence present) --------------------
        linked = by_type.get("KNOWLEDGE_EVIDENCE_LINKED", 0)
        kn_total = sum(v for k, v in by_type.items() if k.startswith("KNOWLEDGE_"))
        knowledge_quality = C.clamp01(C.safe_ratio_0_1(linked, max(1, kn_total))) if kn_total else 0.0
        metrics.append(_q("knowledge_quality", knowledge_quality, "ratio", kn_total > 0,
                          "fraction of knowledge events that link evidence", ["event"]))

        # --- graph integrity (all edges reference real, registered endpoints) -
        graph_integrity = 0.0
        graph_obs = view.has_graph()
        if graph_obs:
            g = view.graph()
            edge_ids = g.list_edges()
            if edge_ids:
                ok = sum(1 for eid in edge_ids
                         if g.has_node(g.edge(eid).source_node)
                         and g.has_node(g.edge(eid).target_node))
                graph_integrity = C.safe_ratio_0_1(ok, len(edge_ids))
            else:
                graph_integrity = 1.0  # vacuously consistent (nodes only)
        metrics.append(_q("graph_integrity", graph_integrity, "ratio", graph_obs,
                          "fraction of edges with registered endpoints (no graph-only truth)",
                          ["graph_edge"]))

        # --- analytics integrity (every source ref resolves to a real id) ----
        # This dimension is verified structurally at validation time; here we
        # expose the share of upstream artifacts that carry lineage (traceable).
        refs = view.source_refs()
        traceable = sum(1 for r in refs if r.lineage_id)
        analytics_integrity = C.safe_ratio_0_1(traceable, max(1, len(refs))) if refs else 0.0
        metrics.append(_q("analytics_integrity", analytics_integrity, "ratio", bool(refs),
                          "fraction of upstream sources that are lineage-traceable",
                          ["event", "workflow", "graph_node"]))

        return metrics
