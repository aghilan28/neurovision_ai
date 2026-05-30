"""Version identities for the Operational Knowledge Graph (V3-P4).

Every graph artifact (node, edge, relationship, projection) records the versions
that produced it, so it is reproducible and auditable for its whole lifetime
(AP-5/AP-6/AP-9, NR-10/NR-11).

The graph is **derived** from existing artifacts (V2 entities, V3 events/timelines/
workflows) — there is no graph-only truth — and is built deterministically (no
wall-clock).
"""

from __future__ import annotations

OPERATIONAL_GRAPH_VERSION: str = "operational-graph@1.0.0"

GRAPH_DOMAIN_VERSION: str = "graph-domain@1.0.0"
GRAPH_IDENTITY_VERSION: str = "graph-identity@1.0.0"
GRAPH_ONTOLOGY_VERSION: str = "graph-ontology@1.0.0"
GRAPH_NODE_VERSION: str = "graph-node@1.0.0"
GRAPH_EDGE_VERSION: str = "graph-edge@1.0.0"
GRAPH_PROJECTION_VERSION: str = "graph-projection@1.0.0"
GRAPH_REGISTRY_VERSION: str = "graph-registry@1.0.0"
GRAPH_AUDIT_VERSION: str = "graph-audit@1.0.0"
GRAPH_LINEAGE_VERSION: str = "graph-lineage@1.0.0"
GRAPH_VALIDATION_VERSION: str = "graph-validation@1.0.0"
GRAPH_QUERY_VERSION: str = "graph-query@1.0.0"
GRAPH_REPORT_VERSION: str = "graph-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
