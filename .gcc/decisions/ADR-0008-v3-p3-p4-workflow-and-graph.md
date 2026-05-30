# ADR-0008 — V3-P3 Workflow Intelligence Layer + V3-P4 Operational Knowledge Graph

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V3-P3 + V3-P4
> **Builds on:** ADR-0001…ADR-0007
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V3-P3 Workflow Intelligence Layer and V3-P4 Operational Knowledge
Graph are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

V3 (P1/P2) gave the platform events and time. It still could not answer *how work
flows, where bottlenecks are, which entities relate, how operational structure
emerges*. V3-P3 makes the **workflow** a first-class entity; V3-P4 builds the first
platform-wide **operational graph**. Both must evolve the existing operational
foundations — not replace event/temporal semantics, not create parallel lineage or
audit systems.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/workflow_intelligence` (V3-P3) and `backend/operational_graph` (V3-P4)
populate the Application layer. They import `ml` + sibling `backend` subsystems;
never `frontend` (enforced by `tests/test_boundaries.py`). No layer is added or
re-drawn.

### D2 — Everything is derived; no hidden state, no graph-only truth
Workflows are derived strictly from events (read via the V3-P2 `EventSourceView`),
reusing the V3-P2 `_STATE_OF` transition map so workflow and temporal evolution
stay consistent. Graph nodes/edges are derived from existing artifacts: every node
carries a real `source_id`, every edge is `derived_from` real artifacts. The
governance "risk" dimension fails any workflow not derived from events and any
graph artifact not derived from a real source — mechanizing "no hidden workflow
state" and "no graph-only truth".

### D3 — No parallel lineage/audit; shared mechanisms reused (directive mandate)
Both subsystems **share** the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog`. Workflow lineage nodes parent the event/timeline nodes;
graph lineage nodes parent the source/endpoint nodes — so `verify_chain` from a
workflow or graph artifact reaches the patient. They keep their own *registries*
(for the new artifact kinds) but never duplicate lineage/audit or wrap existing
registries.

### D4 — Time stays a deterministic logical clock (NR-9/NR-10)
Workflow "durations" are counts of ordered **logical steps** (event positions), not
physical time. Identical inputs reproduce identical workflows, nodes, edges,
versions, and audit heads. Timestamps were rejected as non-reproducible.

### D5 — A practical, closed, extensible ontology (V3-P4)
The graph ontology is a closed set of node/edge types plus relationship rules that
constrain which edge types connect which node types. It is deliberately small
("do not overengineer"): one authority `edge_allowed(...)` is used by the
relationship engine (drops invalid edges), the validator, and the gate. New types
may be added per version; existing pairings are immutable per version.

### D6 — Graph is a model, exposed via services only — no UI (NR-13)
V3-P4 ships node/edge/relationship/projection domain, a registry+adjacency index,
a read-only query layer (lookup, dependency/lineage/workflow traversal, bounded
neighborhood), and derived projections. It implements **no UI and no
visualization** — honoring the forbidden-work list and the directive's "only graph
services".

### D7 — Reuse + tests in top-level `tests/` (ADR-0001 D4)
`ml.provenance.hash_obj`, `ml.lineage`, `ml.validation.ValidationReport`, and the
shared `ImmutableAuditLog` are reused. Tests live in `tests/`
(`test_workflow_intelligence.py`, `test_operational_graph.py`,
`test_v3_p3_p4_e2e.py`); `scripts/verify_v3_p3_p4.py` checks all 21 criteria.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → Event → Timeline → **Workflow → Graph →
  Relationship Model** (`python -m scripts.verify_v3_p3_p4` → all 21 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V2 and V3-P1/P2 remain intact (workflows/graph only *read* them).
  300 tests pass.

## 4. Scope guard (explicitly NOT built — NR-13)

Operational analytics layer, operational recommendations, operational dashboards,
graph UI/visualization (only services), realtime systems, FHIR/HL7/EMR, and any V4
feature.

## 5. Follow-ups / recorded debt (NR-2)

- A future presentation layer can surface workflows/graph in the Clinical
  Workstation by extending the snapshot builder (no domain import in `frontend`).
- Durable, checksummed persistence for the workflow/graph registries (the inherited
  V2 Gap G3) remains the natural next increment.
