# `backend/workflow_intelligence/` — Workflow Intelligence Layer (V3-P3)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P3)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9, NR-9/NR-10/NR-11; ADR-0008

Teaches the platform to understand **workflows**: work, flow, progression,
transitions, dependencies, bottlenecks, efficiency, and operational behavior. The
**workflow itself is a first-class entity**.

---

## Derived from events + temporal intelligence — no hidden workflow state
Every workflow is computed from the recorded events (V3-P1), read through the
shared, deterministically-ordered `EventSourceView` (V3-P2). Transition semantics
reuse the V3-P2 `_STATE_OF` map, so workflow and temporal evolution stay
consistent. Nothing reconstructs hidden state.

## Engines
| Engine | Module | Produces |
|--------|--------|----------|
| Transitions | `transitions/` | ordered state changes + transition frequencies |
| Dependencies | `dependencies/` | upstream/downstream/blocked/waiting/completed edges |
| Bottlenecks | `bottlenecks/` | slow transitions, repeated rework, stalls, wait states, dependency congestion |
| Efficiency | `efficiency/` | completion rate, transition durations (logical steps), rework rate, throughput, operational velocity, workflow health score |

`analytics/` (the `WorkflowBuilder`) combines them into one derived
`WorkflowRecord`.

## Durations are logical steps (NR-9/NR-10)
The platform forbids wall-clock, so transition "durations" are counts of ordered
**logical steps** (event positions) — reproducible, not physical time.

## Governance, audit, lineage, registry
Each workflow passes the `WorkflowGovernanceGate` (architecture/quality/context/
**risk = derived-from-events**), then gets a shared-lineage node parented by the
**event** (and optionally **timeline**) nodes it derives from, an immutable
hash-chained audit event, a content-addressed version, and a registry record.
`verify_chain` spans Patient → … → Event → (Timeline) → Workflow. No workflow
exists outside the registry. Shares the single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog`.

## Quick start
```python
from backend.workflow_intelligence import WorkflowIntelligenceService, EntityRef

wi = WorkflowIntelligenceService(event_service).load_events(all_events)
wf = wi.build_workflow(workflow_type="case_workflow", subject_kind="case",
                       subject_id=case_id, source_entity_ids=[case_id],
                       dependency_refs=[EntityRef(case_id, "case", None, completed=True)])
assert wi.validate(wf).ok
```

Run the tests: `pytest tests/test_workflow_intelligence.py`.
See [`docs/V3_P3_WORKFLOW_INTELLIGENCE.md`](./docs/V3_P3_WORKFLOW_INTELLIGENCE.md).

## Scope guard (NOT built — NR-13)
No operational analytics layer/recommendations/dashboards, no realtime, no
FHIR/HL7/EMR, no V4 features.
