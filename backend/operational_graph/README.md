# `backend/operational_graph/` — Operational Knowledge Graph (V3-P4)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P4)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9, NR-9/NR-10/NR-11; ADR-0008

The first platform-wide graph: a **structured operational model** of the entire
system.

> It is **not** a visualization, **not** a dashboard, **not** a database
> replacement. It is a structured model.

---

## Derived — no graph-only truth
Every node references a real source artifact (`source_id`); every edge is
`derived_from` real artifacts and validated against the ontology. The graph is
derived from V2 entities (patient/case/review/finding/knowledge/decision) and V3
events/timelines/workflows. Node identity is *source-addressed*, so the same source
always maps to the same node.

## Domain
`GraphNode` · `GraphEdge` · `GraphRelationship` · `GraphProjection` + version/audit/
lineage/registry projections (`nodes/domain.py`; `edges/` re-exports `GraphEdge`).

## Ontology (`ontology/`)
Closed node types (patient/case/review/finding/knowledge/decision/event/timeline/
workflow/analytics) and edge types (owns/contains/depends_on/produces/consumes/
influences/precedes/follows/related_to/derived_from), with **relationship rules**
constraining which edge types may connect which node types. Practical, not
over-engineered; extensible per version.

## Engines & services
| Part | Module | Role |
|------|--------|------|
| Relationship engine | `relationships/` | derive nodes + edges from a `GraphInput` (drops ontology-invalid edges) |
| Registry + index | `registry/` | stores nodes/edges/relationships/projections + adjacency |
| Query layer | `queries/` | node/relationship lookup, dependency/lineage/workflow traversal, neighborhood — **no UI** |
| Projections | `projections/` | derived views (case/review/finding/knowledge/workflow/operational) |

## Governance, audit, lineage
Each node/edge/projection passes the `GraphGovernanceGate` (architecture =
ontology-valid, quality = well-formed id, context = lineage parents, **risk =
derived from a real source**), gets a shared-lineage node parented by the source/
endpoint nodes, an immutable audit event, a content-addressed version, and a
registry record. `verify_chain` from a graph artifact reaches the patient. Shares
the single `ml.lineage.LineageTracker` and shared `ImmutableAuditLog`.

## Quick start
```python
from backend.operational_graph import (
    OperationalGraphService, GraphInput, NodeSpec, EdgeSpec, NodeType, EdgeType)

g = OperationalGraphService(lineage_tracker=case_service.lineage)
gi = (GraphInput()
      .add_node(NodeSpec(NodeType.PATIENT, patient_id, patient_lineage))
      .add_node(NodeSpec(NodeType.CASE, case_id, case_lineage))
      .add_edge(EdgeSpec(EdgeType.OWNS, patient_id, case_id, derived_from=(case_id,))))
g.build_graph(gi)
nb = g.queries.neighborhood(g.registry.node_by_source(case_id).node_id, depth=2)
```

Run the tests: `pytest tests/test_operational_graph.py`.
See [`docs/V3_P4_OPERATIONAL_GRAPH.md`](./docs/V3_P4_OPERATIONAL_GRAPH.md).

## Scope guard (NOT built — NR-13)
No operational analytics layer/recommendations/dashboards, **no UI/visualization**
(only graph services), no realtime, no FHIR/HL7/EMR, no V4 features.
