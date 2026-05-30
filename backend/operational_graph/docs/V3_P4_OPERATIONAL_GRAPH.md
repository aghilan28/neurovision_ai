# V3-P4 — Operational Knowledge Graph

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0008](../../../.gcc/decisions/ADR-0008-v3-p3-p4-workflow-and-graph.md)

The first platform-wide graph — a structured operational model of the whole system.
Not a visualization, not a dashboard, not a database replacement.

## 1. Data flow (derived; no graph-only truth)
```
V2 entities + V3 events/timelines/workflows
        │  (read-only refs)
        ▼
relationships.RelationshipEngine  ──▶ GraphNode[] (source-addressed) + GraphEdge[] (ontology-checked)
        │
        ▼   per artifact: gate ▶ lineage(parents=source/endpoint nodes) ▶ audit ▶ version ▶ registry
GraphRegistry (+ adjacency index)
        │
        ├──▶ queries.GraphQueryService   (lookup / dependency / lineage / workflow traversal / neighborhood)
        └──▶ projections.ProjectionEngine (derived views: case/review/finding/knowledge/workflow/operational)
```

## 2. Ontology
Closed node + edge type sets and relationship rules (which edge types connect which
node types). `edge_allowed(edge_type, src_type, dst_type)` is the single authority;
the relationship engine drops invalid edges and the validator/gate reject them.
Practical and extensible: new types may be added; existing pairings are immutable
per version.

## 3. Nodes, edges, projections
- **GraphNode** — represents a real source artifact (`source_id`); identity is
  `gnode+sha16(node_type, source_id)`.
- **GraphEdge** — directed, typed, weighted; `derived_from` real artifacts; identity
  `gedge+sha16(edge_type, src_node, dst_node)`.
- **GraphProjection** — a derived view (induced subgraph) for a scope.

## 4. Query layer (graph services only; no UI)
Node/relationship lookup, neighborhood (bounded BFS), and directed traversals:
dependency (`depends_on`), lineage (`derived_from`), workflow (`contains`/
`produces`/`precedes`). All deterministic and terminating.

## 5. Governance, lineage, determinism
Every artifact passes the gate (architecture = ontology, quality = id, context =
lineage parents, **risk = derived from a real source**), is audited immutably,
versioned by content, and registered. Node lineage parents are the represented
source nodes, so `verify_chain` reaches the patient. No wall-clock anywhere.

## 6. Scope guard (NOT built)
No operational analytics layer/recommendations/dashboards, no UI/visualization
(only services), no realtime, no FHIR/HL7/EMR, no V4.
