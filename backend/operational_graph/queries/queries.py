"""Graph query layer (V3-P4) — graph services only (no UI, no visualization).

Deterministic, read-only traversals over the :class:`GraphRegistry` adjacency
index: node/relationship lookup, dependency/lineage/workflow traversal, and
neighborhood exploration. Traversals visit nodes in sorted, deterministic order and
cap depth to remain reproducible and terminating.
"""

from __future__ import annotations

from typing import Optional

from ..ontology import EdgeType
from ..version import GRAPH_QUERY_VERSION


class GraphQueryService:
    """Read-only query/traversal services over a registered graph."""

    def __init__(self, registry) -> None:
        self.registry = registry

    # --- lookups --------------------------------------------------------------
    def node_lookup(self, node_id: str) -> dict:
        return self.registry.node(node_id).to_dict()

    def node_by_source(self, source_id: str) -> Optional[dict]:
        n = self.registry.node_by_source(source_id)
        return n.to_dict() if n else None

    def relationship_lookup(self, node_id: str) -> dict:
        return {
            "node_id": node_id,
            "out_edges": [e.to_dict() for e in self.registry.out_edges(node_id)],
            "in_edges": [e.to_dict() for e in self.registry.in_edges(node_id)],
        }

    # --- neighborhood ---------------------------------------------------------
    def neighborhood(self, node_id: str, *, depth: int = 1) -> dict:
        """Breadth-first neighborhood up to ``depth`` (deterministic order)."""
        if not self.registry.has_node(node_id):
            raise KeyError(f"node {node_id!r} not in graph")
        seen = {node_id}
        frontier = [node_id]
        edges_seen: set[str] = set()
        for _ in range(max(0, depth)):
            nxt: list[str] = []
            for nid in sorted(frontier):
                for e in self.registry.out_edges(nid) + self.registry.in_edges(nid):
                    edges_seen.add(e.edge_id)
                    for other in (e.source_node, e.target_node):
                        if other not in seen:
                            seen.add(other)
                            nxt.append(other)
            frontier = nxt
        return {"root": node_id, "depth": depth, "nodes": sorted(seen),
                "edges": sorted(edges_seen)}

    # --- traversals -----------------------------------------------------------
    def _traverse(self, node_id: str, edge_types: Optional[set], *, direction: str,
                  max_depth: int = 50) -> list[str]:
        """Deterministic directed traversal following the given edge types."""
        if not self.registry.has_node(node_id):
            raise KeyError(f"node {node_id!r} not in graph")
        order: list[str] = []
        seen = {node_id}
        stack = [(node_id, 0)]
        while stack:
            cur, d = stack.pop()
            if d >= max_depth:
                continue
            edges = (self.registry.out_edges(cur) if direction == "out"
                     else self.registry.in_edges(cur))
            for e in sorted(edges, key=lambda x: x.edge_id):
                if edge_types is not None and e.edge_type not in edge_types:
                    continue
                nxt = e.target_node if direction == "out" else e.source_node
                if nxt not in seen:
                    seen.add(nxt)
                    order.append(nxt)
                    stack.append((nxt, d + 1))
        return order

    def dependency_traversal(self, node_id: str) -> list[str]:
        """Follow depends_on edges downstream from a node."""
        return self._traverse(node_id, {EdgeType.DEPENDS_ON}, direction="out")

    def lineage_traversal(self, node_id: str) -> list[str]:
        """Follow derived_from edges (graph view of derivation)."""
        return self._traverse(node_id, {EdgeType.DERIVED_FROM}, direction="out")

    def workflow_traversal(self, node_id: str) -> list[str]:
        """Follow contains/produces/precedes edges (operational flow)."""
        return self._traverse(node_id, {EdgeType.CONTAINS, EdgeType.PRODUCES, EdgeType.PRECEDES},
                              direction="out")

    def query(self, *, node_type: Optional[str] = None, edge_type: Optional[str] = None) -> dict:
        """A simple structured query over node/edge types (no UI)."""
        nodes = (self.registry.nodes_by_type(node_type) if node_type
                 else self.registry.list_nodes())
        edges = (self.registry.edges_by_type(edge_type) if edge_type
                 else self.registry.list_edges())
        return {"query_version": GRAPH_QUERY_VERSION, "node_type": node_type,
                "edge_type": edge_type, "nodes": nodes, "edges": edges}
