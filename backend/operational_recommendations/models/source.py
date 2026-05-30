"""Deterministic recommendation source view (V3-P6).

A single, read-only bundle over the operational intelligence the recommendation
engines reason on: the V3-P5 **analytics records** (the primary input), plus the
V3-P3 **workflows** and the V3-P4 **graph registry** (for linking + evidence). This
is the only way recommendations read upstream state — nothing is invented, so every
recommendation is reproducible, evidence-linked, and analytics-linked.

The view exposes upstream **lineage ids** (from analytics records, workflows and
graph nodes) so the service can parent recommendation lineage nodes on the
artifacts they cite, keeping ``verify_chain`` reaching the patient.
"""

from __future__ import annotations

from typing import Optional, Sequence


class RecommendationSourceView:
    """An immutable, deterministically-ordered view over operational intelligence."""

    def __init__(self, *, analytics: Sequence = (), workflows: Sequence = (),
                 graph_registry=None) -> None:
        # analytics: Sequence[AnalyticsRecord]; ordered by id for reproducibility
        self._analytics = sorted(analytics, key=lambda a: a.analytics_id)
        self._by_category: dict = {}
        for a in self._analytics:
            self._by_category.setdefault(a.category, []).append(a)
        self._workflows = sorted(workflows, key=lambda w: w.workflow_id)
        self._graph = graph_registry

    # --- analytics ------------------------------------------------------------
    def analytics(self) -> list:
        return list(self._analytics)

    def analytics_of_category(self, category: str) -> list:
        return list(self._by_category.get(category, []))

    def first_of_category(self, category: str) -> Optional[object]:
        recs = self._by_category.get(category, [])
        return recs[0] if recs else None

    def metric(self, category: str, metric_name: str):
        """Return the named metric from the first analytics record of a category."""
        rec = self.first_of_category(category)
        if rec is None:
            return None
        return rec.metric(metric_name)

    def metric_value(self, category: str, metric_name: str, default: float = 0.0) -> float:
        m = self.metric(category, metric_name)
        return m.value if (m is not None and m.observed) else default

    # --- workflows ------------------------------------------------------------
    def workflows(self) -> list:
        return list(self._workflows)

    def workflow_ids(self) -> list:
        return [w.workflow_id for w in self._workflows]

    # --- graph ----------------------------------------------------------------
    def has_graph(self) -> bool:
        return self._graph is not None

    def graph(self):
        return self._graph

    def graph_node_ids(self) -> list:
        return self._graph.list_nodes() if self._graph is not None else []

    # --- lineage parents ------------------------------------------------------
    def analytics_parents(self) -> tuple:
        return tuple(a.lineage_id for a in self._analytics if getattr(a, "lineage_id", None))

    def workflow_parents(self) -> tuple:
        return tuple(w.lineage_id for w in self._workflows if getattr(w, "lineage_id", None))

    def graph_parents(self) -> tuple:
        if self._graph is None:
            return ()
        out = []
        for nid in self._graph.list_nodes():
            lid = getattr(self._graph.node(nid), "lineage_id", None)
            if lid:
                out.append(lid)
        return tuple(out)

    def all_parents(self) -> tuple:
        """De-duplicated upstream lineage parents (analytics + workflows + graph)."""
        seen: list[str] = []
        for lid in (self.analytics_parents() + self.workflow_parents() + self.graph_parents()):
            if lid and lid not in seen:
                seen.append(lid)
        return tuple(seen)

    def analytics_lineage_by_id(self) -> dict:
        return {a.analytics_id: getattr(a, "lineage_id", None) for a in self._analytics}
