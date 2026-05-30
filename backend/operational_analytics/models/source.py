"""Deterministic analytics source view (V3-P5).

A single, read-only, deterministically-ordered bundle over the already-governed
upstream artifacts the analytics engines derive intelligence from:

  * events (V3-P1)            — via the temporal :class:`EventSourceView`
  * workflows (V3-P3)         — first-class workflow records
  * operational graph (V3-P4) — a read-only :class:`GraphRegistry`
  * temporal analytics (V3-P2)— optional duration metrics

This is the *only* way analytics reads upstream state — nothing is reconstructed
or invented, so every analytics artifact is reproducible and derived (no
analytics-only truth). The view also exposes the upstream **lineage ids** so the
service can parent analytics lineage nodes on the artifacts they summarize, keeping
``verify_chain`` reaching the patient.
"""

from __future__ import annotations

from typing import Optional, Sequence

from backend.temporal_intelligence.timelines import EventSourceView

from .domain import AnalyticsSourceRef


class AnalyticsSourceView:
    """An immutable, deterministically-ordered view over upstream artifacts."""

    def __init__(self, *, events: Sequence = (), workflows: Sequence = (),
                 graph_registry=None, temporal_analytics=None) -> None:
        self._events_view = EventSourceView(list(events))
        # workflows ordered deterministically by id for reproducibility
        self._workflows = sorted(workflows, key=lambda w: w.workflow_id)
        self._graph = graph_registry
        self._temporal = temporal_analytics

    # --- events ---------------------------------------------------------------
    def events(self) -> list:
        return self._events_view.all()

    def events_view(self) -> EventSourceView:
        return self._events_view

    def events_for_sources(self, source_entity_ids: Sequence[str]) -> list:
        return self._events_view.for_sources(source_entity_ids)

    def event_counts_by_category(self) -> dict:
        counts: dict = {}
        for e in self._events_view.all():
            counts[e.category] = counts.get(e.category, 0) + 1
        return dict(sorted(counts.items()))

    def event_counts_by_type(self) -> dict:
        counts: dict = {}
        for e in self._events_view.all():
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return dict(sorted(counts.items()))

    # --- workflows ------------------------------------------------------------
    def workflows(self) -> list:
        return list(self._workflows)

    def workflows_of_type(self, workflow_type: str) -> list:
        return [w for w in self._workflows if w.workflow_type == workflow_type]

    def workflow_for_subject(self, subject_id: str) -> Optional[object]:
        for w in self._workflows:
            if w.subject_id == subject_id:
                return w
        return None

    # --- graph ----------------------------------------------------------------
    def has_graph(self) -> bool:
        return self._graph is not None

    def graph(self):
        return self._graph

    def graph_node_ids(self) -> list:
        return self._graph.list_nodes() if self._graph is not None else []

    def graph_edge_ids(self) -> list:
        return self._graph.list_edges() if self._graph is not None else []

    # --- temporal analytics ---------------------------------------------------
    def has_temporal(self) -> bool:
        return self._temporal is not None

    def temporal_analytics(self):
        return self._temporal

    # --- lineage parents / source refs ---------------------------------------
    def event_parents(self) -> tuple:
        return tuple(e.lineage_id for e in self._events_view.all()
                     if getattr(e, "lineage_id", None))

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

    def temporal_parents(self) -> tuple:
        if self._temporal is None:
            return ()
        lid = getattr(self._temporal, "lineage_id", None)
        return (lid,) if lid else ()

    def source_refs(self, *, include_events=True, include_workflows=True,
                    include_graph=True, include_temporal=True) -> tuple:
        """The upstream artifacts an analytics record derives from (read-only refs)."""
        refs: list[AnalyticsSourceRef] = []
        if include_events:
            for e in self._events_view.all():
                refs.append(AnalyticsSourceRef(e.event_id, "event", getattr(e, "lineage_id", None)))
        if include_workflows:
            for w in self._workflows:
                refs.append(AnalyticsSourceRef(w.workflow_id, "workflow",
                                               getattr(w, "lineage_id", None)))
        if include_graph and self._graph is not None:
            for nid in self._graph.list_nodes():
                refs.append(AnalyticsSourceRef(nid, "graph_node",
                                               getattr(self._graph.node(nid), "lineage_id", None)))
        if include_temporal and self._temporal is not None:
            refs.append(AnalyticsSourceRef(self._temporal.analytics_id, "temporal_analytics",
                                           getattr(self._temporal, "lineage_id", None)))
        return tuple(refs)

    def all_parents(self) -> tuple:
        """De-duplicated upstream lineage parents (events + workflows + graph + temporal)."""
        seen: list[str] = []
        for lid in (self.event_parents() + self.workflow_parents()
                    + self.graph_parents() + self.temporal_parents()):
            if lid and lid not in seen:
                seen.append(lid)
        return tuple(seen)
