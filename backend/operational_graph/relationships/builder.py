"""Relationship engine (V3-P4) — derive nodes + edges from existing artifacts.

Deterministically builds the operational graph from already-registered artifacts:
V2 entities (patient/case/review/finding/knowledge/decision), V3 events, timelines,
and workflows. Every node references a real ``source_id`` and every edge is justified
by a source artifact (``derived_from``) and validated against the ontology — so there
is no graph-only truth.

The engine is a pure builder over a :class:`GraphInput` bundle of read-only refs;
it performs no I/O and no mutation of any source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from ..identity import mint_node, mint_edge
from ..nodes.domain import GraphNode, GraphEdge
from ..ontology import edge_allowed


@dataclass(frozen=True)
class NodeSpec:
    """A read-only reference to a source artifact to represent as a node."""

    node_type: str
    source_id: str
    source_lineage_id: Optional[str] = None
    label: str = ""
    attributes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeSpec:
    """A requested edge between two source ids with an ontology edge type."""

    edge_type: str
    source_source_id: str          # source node's source_id
    target_source_id: str          # target node's source_id
    weight: float = 1.0
    derived_from: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)


@dataclass
class GraphInput:
    """The read-only bundle the relationship engine derives the graph from."""

    nodes: list = field(default_factory=list)      # list[NodeSpec]
    edges: list = field(default_factory=list)      # list[EdgeSpec]

    def add_node(self, spec: NodeSpec) -> "GraphInput":
        self.nodes.append(spec)
        return self

    def add_edge(self, spec: EdgeSpec) -> "GraphInput":
        self.edges.append(spec)
        return self


class RelationshipEngine:
    """Builds graph nodes + edges from a :class:`GraphInput` (read-only)."""

    def build_nodes(self, graph_input: GraphInput) -> list[GraphNode]:
        nodes: dict[str, GraphNode] = {}
        for spec in graph_input.nodes:
            ident = mint_node(spec.node_type, spec.source_id)
            if ident.id in nodes:
                continue  # identical source -> identical node (idempotent)
            nodes[ident.id] = GraphNode(
                node_id=ident.id, node_type=spec.node_type, source_id=spec.source_id,
                source_lineage_id=spec.source_lineage_id, label=spec.label or spec.node_type,
                attributes=dict(spec.attributes))
        return [nodes[k] for k in sorted(nodes)]

    def build_edges(self, graph_input: GraphInput, nodes: Sequence[GraphNode]) -> list[GraphEdge]:
        # index source_id -> node
        by_source = {n.source_id: n for n in nodes}
        edges: dict[str, GraphEdge] = {}
        for spec in graph_input.edges:
            src = by_source.get(spec.source_source_id)
            dst = by_source.get(spec.target_source_id)
            if src is None or dst is None:
                continue  # endpoints must resolve to real nodes (no graph-only truth)
            if not edge_allowed(spec.edge_type, src.node_type, dst.node_type):
                continue  # ontology rejects this pairing
            ident = mint_edge(spec.edge_type, src.node_id, dst.node_id)
            if ident.id in edges:
                continue
            edges[ident.id] = GraphEdge(
                edge_id=ident.id, edge_type=spec.edge_type, source_node=src.node_id,
                target_node=dst.node_id, source_type=src.node_type, target_type=dst.node_type,
                weight=spec.weight, derived_from=tuple(spec.derived_from),
                attributes=dict(spec.attributes))
        return [edges[k] for k in sorted(edges)]
