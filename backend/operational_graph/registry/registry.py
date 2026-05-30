"""The graph registry: governed, versioned, traceable graph artifacts (V3-P4).

Stores nodes, edges, relationships and projections. No graph artifact may exist
outside the registry; re-registering the same id + version with different content
is a forbidden silent overwrite. The registry also serves as the **graph index**
the query layer traverses (adjacency by node).
"""

from __future__ import annotations

from ..version import GRAPH_REGISTRY_VERSION
from ..nodes.domain import GraphNode, GraphEdge, GraphRelationship, GraphProjection, GraphRegistryRecord


class GraphRegistry:
    """In-memory registry + adjacency index for the operational graph."""

    def __init__(self) -> None:
        self._records: dict[str, GraphRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._relationships: dict[str, GraphRelationship] = {}
        self._projections: dict[str, GraphProjection] = {}
        # adjacency: node_id -> list[edge_id]
        self._out: dict[str, list[str]] = {}
        self._in: dict[str, list[str]] = {}

    # --- registry bookkeeping -------------------------------------------------
    def _register_record(self, record: GraphRegistryRecord) -> None:
        key = (record.artifact_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"graph artifact {record.artifact_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.artifact_id] = record

    # --- nodes ----------------------------------------------------------------
    def register_node(self, node: GraphNode) -> GraphNode:
        self._register_record(GraphRegistryRecord(
            artifact_id=node.node_id, artifact_kind="node", artifact_type=node.node_type,
            version=node.version, lineage_id=node.lineage_id or "", audit_state=node.audit_state or "",
            content_signature_value=node.state_signature()))
        self._nodes[node.node_id] = node
        self._out.setdefault(node.node_id, [])
        self._in.setdefault(node.node_id, [])
        return node

    def node(self, node_id: str) -> GraphNode:
        if node_id not in self._nodes:
            raise KeyError(f"node {node_id!r} not in graph")
        return self._nodes[node_id]

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def list_nodes(self) -> list[str]:
        return sorted(self._nodes)

    def nodes_by_type(self, node_type: str) -> list[str]:
        return sorted(nid for nid, n in self._nodes.items() if n.node_type == node_type)

    def node_by_source(self, source_id: str) -> GraphNode | None:
        for n in self._nodes.values():
            if n.source_id == source_id:
                return n
        return None

    # --- edges ----------------------------------------------------------------
    def register_edge(self, edge: GraphEdge) -> GraphEdge:
        if edge.source_node not in self._nodes or edge.target_node not in self._nodes:
            raise KeyError("edge endpoints must be registered nodes")
        self._register_record(GraphRegistryRecord(
            artifact_id=edge.edge_id, artifact_kind="edge", artifact_type=edge.edge_type,
            version=edge.version, lineage_id=edge.lineage_id or "", audit_state=edge.audit_state or "",
            content_signature_value=edge.state_signature()))
        self._edges[edge.edge_id] = edge
        self._out.setdefault(edge.source_node, []).append(edge.edge_id)
        self._in.setdefault(edge.target_node, []).append(edge.edge_id)
        return edge

    def edge(self, edge_id: str) -> GraphEdge:
        if edge_id not in self._edges:
            raise KeyError(f"edge {edge_id!r} not in graph")
        return self._edges[edge_id]

    def list_edges(self) -> list[str]:
        return sorted(self._edges)

    def edges_by_type(self, edge_type: str) -> list[str]:
        return sorted(eid for eid, e in self._edges.items() if e.edge_type == edge_type)

    def out_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[eid] for eid in sorted(self._out.get(node_id, []))]

    def in_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[eid] for eid in sorted(self._in.get(node_id, []))]

    # --- relationships --------------------------------------------------------
    def register_relationship(self, rel: GraphRelationship) -> GraphRelationship:
        existing = self._relationships.get(rel.relationship_id)
        if existing is not None and existing.state_signature() != rel.state_signature():
            raise ValueError(f"relationship {rel.relationship_id} already registered differently")
        self._relationships[rel.relationship_id] = rel
        return rel

    def list_relationships(self) -> list[str]:
        return sorted(self._relationships)

    def relationship(self, relationship_id: str) -> GraphRelationship:
        return self._relationships[relationship_id]

    # --- projections ----------------------------------------------------------
    def register_projection(self, proj: GraphProjection) -> GraphProjection:
        self._register_record(GraphRegistryRecord(
            artifact_id=proj.projection_id, artifact_kind="projection",
            artifact_type=proj.projection_type, version=proj.version,
            lineage_id=proj.lineage_id or "", audit_state=proj.audit_state or "",
            content_signature_value=proj.state_signature()))
        self._projections[proj.projection_id] = proj
        return proj

    def projection(self, projection_id: str) -> GraphProjection:
        if projection_id not in self._projections:
            raise KeyError(f"projection {projection_id!r} not in graph")
        return self._projections[projection_id]

    def list_projections(self) -> list[str]:
        return sorted(self._projections)

    # --- generic --------------------------------------------------------------
    def get_record(self, artifact_id: str) -> GraphRegistryRecord:
        if artifact_id not in self._records:
            raise KeyError(f"graph artifact {artifact_id!r} not in registry")
        return self._records[artifact_id]

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._records

    def to_dict(self) -> dict:
        return {
            "graph_registry_version": GRAPH_REGISTRY_VERSION,
            "n_nodes": len(self._nodes), "n_edges": len(self._edges),
            "n_relationships": len(self._relationships), "n_projections": len(self._projections),
            "nodes": {nid: n.to_dict() for nid, n in sorted(self._nodes.items())},
            "edges": {eid: e.to_dict() for eid, e in sorted(self._edges.items())},
            "relationships": {rid: r.to_dict() for rid, r in sorted(self._relationships.items())},
            "projections": {pid: p.to_dict() for pid, p in sorted(self._projections.items())},
        }
