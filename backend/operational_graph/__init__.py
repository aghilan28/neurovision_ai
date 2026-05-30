"""``backend/operational_graph`` — Operational Knowledge Graph (V3-P4).

The first platform-wide graph: a **structured operational model** of the entire
system. It is **not** a visualization, a dashboard, or a database replacement.

The graph is **derived** from existing artifacts (V2 patient/case/review/finding/
knowledge/decision; V3 events/timelines/workflows/analytics) — there is **no
graph-only truth**: every node references a real ``source_id`` and every edge is
``derived_from`` real artifacts and validated against the ontology. It is versioned,
traceable, auditable, lineage-tracked, deterministic, and governed; graph artifact
lineage parents are the source/endpoint nodes, so ``verify_chain`` reaches the
patient. Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit.

Subsystems: nodes + edges (domain), a practical ontology (node/edge types +
relationship rules), a relationship engine (derives nodes/edges), a registry +
adjacency index, a read-only query layer (lookup / dependency / lineage / workflow
traversal / neighborhood — **no UI, no visualization**), derived projections, and
validation/reports.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling subsystems; never imports ``frontend``. Scope is strictly V3-P4 — no
operational analytics layer/recommendations/dashboards, no realtime, no FHIR/HL7/
EMR, no V4. See ``.gcc/decisions/ADR-0008``.
"""

from __future__ import annotations

from .version import (
    OPERATIONAL_GRAPH_VERSION, GRAPH_DOMAIN_VERSION, GRAPH_IDENTITY_VERSION, GRAPH_ONTOLOGY_VERSION,
    GRAPH_NODE_VERSION, GRAPH_EDGE_VERSION, GRAPH_PROJECTION_VERSION, GRAPH_REGISTRY_VERSION,
    GRAPH_AUDIT_VERSION, GRAPH_LINEAGE_VERSION, GRAPH_VALIDATION_VERSION, GRAPH_QUERY_VERSION,
    GRAPH_REPORT_VERSION,
)
from . import ontology
from .ontology import NodeType, EdgeType, OntologyError
from .identity import (
    GraphIdentity, GraphIdentityError, mint_node, mint_edge, mint_projection,
    validate_node_id, validate_edge_id, validate_projection_id,
)
from .nodes import (
    GraphNode, GraphEdge, GraphRelationship, GraphProjection,
    GraphAuditRecord, GraphVersion, GraphLineageRecord, GraphRegistryRecord,
)
from .relationships import NodeSpec, EdgeSpec, GraphInput, RelationshipEngine
from .registry import GraphRegistry
from .queries import GraphQueryService
from .projections import ProjectionEngine
from .audit import make_graph_audit_log
from .validation import GraphGovernanceGate, GraphValidator, GraphValidationError
from .service import OperationalGraphService

__all__ = [
    "OPERATIONAL_GRAPH_VERSION", "GRAPH_DOMAIN_VERSION", "GRAPH_IDENTITY_VERSION",
    "GRAPH_ONTOLOGY_VERSION", "GRAPH_NODE_VERSION", "GRAPH_EDGE_VERSION", "GRAPH_PROJECTION_VERSION",
    "GRAPH_REGISTRY_VERSION", "GRAPH_AUDIT_VERSION", "GRAPH_LINEAGE_VERSION",
    "GRAPH_VALIDATION_VERSION", "GRAPH_QUERY_VERSION", "GRAPH_REPORT_VERSION",
    "ontology", "NodeType", "EdgeType", "OntologyError",
    "GraphIdentity", "GraphIdentityError", "mint_node", "mint_edge", "mint_projection",
    "validate_node_id", "validate_edge_id", "validate_projection_id",
    "GraphNode", "GraphEdge", "GraphRelationship", "GraphProjection",
    "GraphAuditRecord", "GraphVersion", "GraphLineageRecord", "GraphRegistryRecord",
    "NodeSpec", "EdgeSpec", "GraphInput", "RelationshipEngine", "GraphRegistry",
    "GraphQueryService", "ProjectionEngine", "make_graph_audit_log",
    "GraphGovernanceGate", "GraphValidator", "GraphValidationError",
    "OperationalGraphService",
]
