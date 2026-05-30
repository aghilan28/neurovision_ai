# V3-P3 — Workflow Intelligence Layer

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0008](../../../.gcc/decisions/ADR-0008-v3-p3-p4-workflow-and-graph.md)

Makes the workflow a first-class entity and answers: *how does work flow, where are
the bottlenecks, how efficient is it?*

## 1. Data flow (derived from events + temporal intelligence)
```
OperationalEventService (V3-P1) ─▶ EventRecord[] ─load_events─▶ EventSourceView (deterministic order, V3-P2)
                                                                      │
        ┌──────────────────┬──────────────────┬─────────────────────┴────────┐
        ▼                  ▼                  ▼                              ▼
  transitions/        dependencies/       bottlenecks/                  efficiency/
        └───────────────── analytics.WorkflowBuilder ─▶ WorkflowRecord ──────┘
                          governance gate ▶ lineage(parents=event/timeline nodes) ▶ audit ▶ version ▶ registry
```

## 2. WorkflowRecord
A first-class entity: `transitions` (ordered, continuous state changes),
`dependencies` (upstream/downstream/blocked/waiting/completed), `metrics`
(bottleneck + efficiency), `metadata` (source events, detected bottlenecks), and
the latest `state`. Its lineage parents are the event/timeline nodes it derives
from.

## 3. Bottlenecks (deterministic detectors)
slow_transitions (logical-step gap > threshold), repeated_rework (a state
re-entered), workflow_stall (events but ≤1 transition), excessive_wait_states
(blocked/waiting dependencies), dependency_congestion (an entity with many
dependents).

## 4. Efficiency metrics
completion_rate, mean_transition_steps (logical steps), rework_rate, throughput
(transitions/event), operational_velocity (transitions/span), and a composite
workflow_health_score in [0,1].

## 5. Determinism, lineage, governance
No wall-clock; durations are logical steps. Every workflow passes the gate
(architecture/quality/context/**risk = derived-from-events**), is audited
immutably, versioned by content, registered, and traceable to the patient via
`verify_chain`.

## 6. Scope guard (NOT built)
No operational analytics layer/recommendations/dashboards, realtime, FHIR/HL7/EMR,
or V4.
