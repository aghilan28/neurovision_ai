"""Graph projections (V3-P4) — derived graph views.

A projection is a deterministic subset of the graph (node ids + the edges induced
among them) for a scope. Projections are derived views — they add no truth; they
select existing registered nodes/edges.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..identity import mint_projection
from ..nodes.domain import GraphProjection


class ProjectionEngine:
    """Builds :class:`GraphProjection` views from a registered graph (read-only)."""

    def __init__(self, registry) -> None:
        self.registry = registry

    def _induced(self, node_ids: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        node_set = set(node_ids)
        edge_ids = []
        for nid in node_ids:
            for e in self.registry.out_edges(nid):
                if e.target_node in node_set:
                    edge_ids.append(e.edge_id)
        return tuple(sorted(node_set)), tuple(sorted(set(edge_ids)))

    def by_node_types(self, projection_type: str, node_types: Sequence[str], *,
                      scope: Optional[str] = None) -> GraphProjection:
        node_ids = []
        for nt in node_types:
            node_ids += self.registry.nodes_by_type(nt)
        nodes, edges = self._induced(node_ids)
        scope = scope or f"{projection_type}:{'+'.join(node_types)}"
        ident = mint_projection(projection_type, scope)
        return GraphProjection(projection_id=ident.id, projection_type=projection_type,
                               scope=scope, node_ids=nodes, edge_ids=edges)

    def operational(self) -> GraphProjection:
        """The whole-graph operational projection (all nodes + all edges)."""
        nodes = tuple(self.registry.list_nodes())
        edges = tuple(self.registry.list_edges())
        ident = mint_projection("operational", "operational:all")
        return GraphProjection(projection_id=ident.id, projection_type="operational",
                               scope="operational:all", node_ids=nodes, edge_ids=edges)
