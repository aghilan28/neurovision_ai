"""OperationalGraphService — the governed orchestration hub for V3-P4.

Builds the platform-wide **operational graph** — a structured operational model
**derived** from existing artifacts (V2 entities, V3 events/timelines/workflows).
It is not a visualization, a dashboard, or a database replacement.

Every node/edge/projection is admitted through one governed path: governance gate
(architecture/quality/context/risk) → shared-lineage node parented by the source
artifact lineage node(s) → immutable audit event → content-addressed version →
registry sync. Because node lineage parents are the represented source nodes (which
trace to the patient), ``verify_chain`` from any graph artifact reaches the patient.
Shares the platform's single ``ml.lineage.LineageTracker``; no graph-only truth.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .relationships import GraphInput, RelationshipEngine
from .nodes.domain import GraphNode, GraphEdge, GraphProjection, GraphVersion
from .registry import GraphRegistry
from .audit import make_graph_audit_log
from .lineage import make_graph_lineage
from .validation import GraphGovernanceGate, GraphValidator
from .queries import GraphQueryService
from .projections import ProjectionEngine
from .reports import (
    build_graph_summary_report, build_node_report, build_edge_report, build_relationship_report,
    build_projection_report, build_validation_report, build_audit_report,
)


class OperationalGraphService:
    """Stateful service: graph registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[GraphRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or GraphRegistry()
        self.audit = make_graph_audit_log()
        self.gate = GraphGovernanceGate()
        self.validator = GraphValidator()
        self._engine = RelationshipEngine()
        self.queries = GraphQueryService(self.registry)
        self.projections = ProjectionEngine(self.registry)

    # --- build the graph from derived nodes/edges -----------------------------
    def build_graph(self, graph_input: GraphInput, *, created_at: str = DETERMINISTIC_EPOCH):
        """Derive + admit all nodes then all edges from a GraphInput bundle."""
        nodes = self._engine.build_nodes(graph_input)
        for node in nodes:
            self._admit_node(node, created_at=created_at)
        edges = self._engine.build_edges(graph_input, [self.registry.node(n.node_id) for n in nodes])
        for edge in edges:
            self._admit_edge(edge, created_at=created_at)
        return {"n_nodes": len(nodes), "n_edges": len(edges)}

    # --- admission ------------------------------------------------------------
    def _admit_node(self, node: GraphNode, *, created_at: str) -> GraphNode:
        parents = (node.source_lineage_id,) if node.source_lineage_id else ()
        report = self.gate.evaluate(artifact=node, parents=parents,
                                    requires_lineage=bool(parents))
        self.gate.raise_if_failed(report)
        lin = self.lineage.record(make_graph_lineage("graph_node", node.node_id, parents=parents,
                                                    graph_kind=node.node_type, created_at=created_at))
        self.audit.append("node_created", {"node_id": node.node_id, "node_type": node.node_type,
                                           "lineage_id": lin.lineage_id}, created_at=created_at)
        version = GraphVersion.compute(node.state_signature(), None)
        node = replace(node, version=version, lineage_id=lin.lineage_id, audit_state=self.audit.head)
        self.audit.append("version_changed", {"node_id": node.node_id, "version": version},
                          created_at=created_at)
        node = replace(node, audit_state=self.audit.head)
        self.registry.register_node(node)
        self.audit.append("node_registered", {"node_id": node.node_id}, created_at=created_at)
        node = replace(node, audit_state=self.audit.head)
        # re-register so the stored node carries the final audit_state
        self.registry.register_node(node)
        return node

    def _admit_edge(self, edge: GraphEdge, *, created_at: str) -> GraphEdge:
        src = self.registry.node(edge.source_node)
        dst = self.registry.node(edge.target_node)
        parents = tuple(p for p in (src.lineage_id, dst.lineage_id) if p)
        report = self.gate.evaluate(artifact=edge, parents=parents, requires_lineage=True)
        self.gate.raise_if_failed(report)
        lin = self.lineage.record(make_graph_lineage("graph_edge", edge.edge_id, parents=parents,
                                                    graph_kind=edge.edge_type, created_at=created_at))
        self.audit.append("edge_created", {"edge_id": edge.edge_id, "edge_type": edge.edge_type,
                                           "lineage_id": lin.lineage_id}, created_at=created_at)
        version = GraphVersion.compute(edge.state_signature(), None)
        edge = replace(edge, version=version, lineage_id=lin.lineage_id, audit_state=self.audit.head)
        self.audit.append("version_changed", {"edge_id": edge.edge_id, "version": version},
                          created_at=created_at)
        edge = replace(edge, audit_state=self.audit.head)
        self.registry.register_edge(edge)
        self.audit.append("edge_registered", {"edge_id": edge.edge_id}, created_at=created_at)
        edge = replace(edge, audit_state=self.audit.head)
        self.registry.register_edge(edge)
        return edge

    def build_projection(self, projection, *, created_at: str = DETERMINISTIC_EPOCH) -> GraphProjection:
        """Admit a derived projection (parents = its included node lineage nodes)."""
        parents = tuple(
            self.registry.node(nid).lineage_id for nid in projection.node_ids
            if self.registry.has_node(nid) and self.registry.node(nid).lineage_id)
        report = self.gate.evaluate(artifact=projection, parents=parents, requires_lineage=bool(parents))
        self.gate.raise_if_failed(report)
        lin = self.lineage.record(make_graph_lineage(
            "graph_projection", projection.projection_id, parents=parents,
            graph_kind=projection.projection_type, created_at=created_at))
        self.audit.append("projection_created",
                          {"projection_id": projection.projection_id, "lineage_id": lin.lineage_id},
                          created_at=created_at)
        version = GraphVersion.compute(projection.state_signature(), None)
        projection = replace(projection, version=version, lineage_id=lin.lineage_id,
                             audit_state=self.audit.head)
        self.audit.append("version_changed",
                          {"projection_id": projection.projection_id, "version": version},
                          created_at=created_at)
        projection = replace(projection, audit_state=self.audit.head)
        self.registry.register_projection(projection)
        self.audit.append("projection_registered", {"projection_id": projection.projection_id},
                          created_at=created_at)
        projection = replace(projection, audit_state=self.audit.head)
        self.registry.register_projection(projection)
        return projection

    # --- validation + reports -------------------------------------------------
    def validate(self, artifact):
        return self.validator.validate(artifact=artifact, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self) -> dict:
        return {
            "graph_summary_report": build_graph_summary_report(self.registry),
            "node_report": build_node_report(self.registry),
            "edge_report": build_edge_report(self.registry),
            "relationship_report": build_relationship_report(self.registry),
            "projection_report": build_projection_report(self.registry),
            "audit_report": build_audit_report(self.audit),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)
