"""Operational graph domain entities (V3-P4).

Pure data + ``to_dict`` + ``state_signature``. The graph is a **structured
operational model derived** from existing artifacts — not a visualization, not a
dashboard, not a database replacement. Every node/edge references a real source
artifact (``source_id``), so there is no graph-only truth.

Mandated entities: ``GraphNode``, ``GraphEdge``, ``GraphRelationship``,
``GraphProjection``, ``GraphVersion``, ``GraphAuditRecord``,
``GraphLineageRecord``, ``GraphRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    GRAPH_NODE_VERSION, GRAPH_EDGE_VERSION, GRAPH_PROJECTION_VERSION,
    GRAPH_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)


@dataclass(frozen=True)
class GraphNode:
    """A node representing a real source artifact (entity/event/timeline/workflow)."""

    node_id: str
    node_type: str
    source_id: str               # the represented artifact's id (no graph-only truth)
    source_lineage_id: Optional[str] = None
    label: str = ""
    attributes: dict = field(default_factory=dict)
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    node_version: str = GRAPH_NODE_VERSION

    def state_signature(self) -> str:
        return hash_obj({"node_id": self.node_id, "node_type": self.node_type,
                         "source_id": self.source_id, "label": self.label,
                         "attributes": self.attributes})

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "node_type": self.node_type, "source_id": self.source_id,
                "source_lineage_id": self.source_lineage_id, "label": self.label,
                "attributes": self.attributes, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "node_version": self.node_version, "state_signature": self.state_signature()}


@dataclass(frozen=True)
class GraphEdge:
    """A directed, typed, weighted edge between two graph nodes."""

    edge_id: str
    edge_type: str
    source_node: str
    target_node: str
    source_type: str
    target_type: str
    weight: float = 1.0
    directed: bool = True
    attributes: dict = field(default_factory=dict)
    derived_from: tuple[str, ...] = ()     # source artifact ids this edge was derived from
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    edge_version: str = GRAPH_EDGE_VERSION

    def state_signature(self) -> str:
        return hash_obj({"edge_id": self.edge_id, "edge_type": self.edge_type,
                         "source_node": self.source_node, "target_node": self.target_node,
                         "source_type": self.source_type, "target_type": self.target_type,
                         "weight": self.weight, "directed": self.directed,
                         "attributes": self.attributes, "derived_from": list(self.derived_from)})

    def to_dict(self) -> dict:
        return {"edge_id": self.edge_id, "edge_type": self.edge_type,
                "source_node": self.source_node, "target_node": self.target_node,
                "source_type": self.source_type, "target_type": self.target_type,
                "weight": self.weight, "directed": self.directed, "attributes": self.attributes,
                "derived_from": list(self.derived_from), "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "edge_version": self.edge_version, "state_signature": self.state_signature()}


@dataclass(frozen=True)
class GraphRelationship:
    """A higher-level, named relationship summarizing one or more edges.

    (e.g. a "case_review_chain" relationship grouping the contains/produces edges
    of a case.) Relationships are derived, versioned summaries — not new truth.
    """

    relationship_id: str
    name: str
    edge_ids: tuple[str, ...]
    description: str = ""

    def state_signature(self) -> str:
        return hash_obj({"relationship_id": self.relationship_id, "name": self.name,
                         "edge_ids": list(self.edge_ids)})

    def to_dict(self) -> dict:
        return {"relationship_id": self.relationship_id, "name": self.name,
                "edge_ids": list(self.edge_ids), "description": self.description,
                "state_signature": self.state_signature()}


@dataclass(frozen=True)
class GraphProjection:
    """A derived graph view: a subset of node/edge ids for a scope."""

    projection_id: str
    projection_type: str         # case|review|finding|knowledge|workflow|operational
    scope: str
    node_ids: tuple[str, ...] = ()
    edge_ids: tuple[str, ...] = ()
    version: str = ""
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    projection_version: str = GRAPH_PROJECTION_VERSION

    @property
    def n_nodes(self) -> int:
        return len(self.node_ids)

    @property
    def n_edges(self) -> int:
        return len(self.edge_ids)

    def state_signature(self) -> str:
        return hash_obj({"projection_id": self.projection_id, "projection_type": self.projection_type,
                         "scope": self.scope, "node_ids": list(self.node_ids),
                         "edge_ids": list(self.edge_ids)})

    def to_dict(self) -> dict:
        return {"projection_id": self.projection_id, "projection_type": self.projection_type,
                "scope": self.scope, "node_ids": list(self.node_ids),
                "edge_ids": list(self.edge_ids), "n_nodes": self.n_nodes, "n_edges": self.n_edges,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "projection_version": self.projection_version,
                "state_signature": self.state_signature()}


# --- audit / version / lineage / registry projections ------------------------
@dataclass(frozen=True)
class GraphAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class GraphVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


@dataclass(frozen=True)
class GraphLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class GraphRegistryRecord:
    artifact_id: str
    artifact_kind: str           # node | edge | projection
    artifact_type: str           # node_type / edge_type / projection_type
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    graph_registry_version: str = GRAPH_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                "artifact_type": self.artifact_type, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "graph_registry_version": self.graph_registry_version,
                "content_signature": self.content_signature()}
