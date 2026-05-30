# `backend/temporal_intelligence/` — Temporal Intelligence Layer (V3-P2)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P2)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9, NR-9/NR-10/NR-11; ADR-0007

Teaches the platform about **time**. Version 2 understood current state; Version 3
understands **state evolution, history, progression, temporal context**, and
**operational timelines**.

---

## Derived from events — no hidden state reconstruction
Every temporal artifact is computed strictly **from the recorded events** (V3-P1)
via a deterministically-ordered `EventSourceView`. Nothing reconstructs hidden
state. Ordering is the events' `LogicalClock` (no wall-clock), so every artifact is
reproducible.

## Artifact families
| Family | Module | Description |
|--------|--------|-------------|
| **Timelines** | `timelines/` | the ordered event sequence for a subject (patient/case/review/finding/knowledge/decision/operational) |
| **Histories** | `history/` | the reconstructed change-log of a subject (with recoverable source versions) |
| **Evolution records** | `evolution/` | the ordered state transitions of a subject |
| **Temporal analytics** | `analytics/` | duration/timing metrics in deterministic *logical steps* |

Plus **visualization contracts** (`schemas/visualization.py`) — *contracts only, no
UI* — for timeline, event_sequence, evolution_graph, duration_graph, trend_graph,
and a future operational_dashboard.

## Durations are logical steps (NR-9/NR-10)
The platform forbids wall-clock, so a "duration" is the number of ordered
operational **logical steps** between two event types (a reproducible event-count
span), not a physical time delta. Unobserved metrics report `steps == -1`.

## Lineage spans Patient → … → Event → Temporal artifact
Each temporal artifact's lineage parents are the **event** nodes it derives from;
since events already trace to the patient, a single `verify_chain` from a timeline/
history/evolution/analytics spans the whole chain. Shares the platform's single
`ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`.

## Validation (`validation/`)
Eight integrity dimensions (identity/registry/audit/lineage/version + timeline/
history/evolution/analytics structural integrity) plus the governance gate
(architecture/quality/context/**risk = derived-from-events**).

## Quick start
```python
from backend.temporal_intelligence import TemporalIntelligenceService

ti = TemporalIntelligenceService(event_service).load_events(all_events)
timeline = ti.build_timeline(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
analytics = ti.build_analytics(scope="operational")
assert ti.validate(timeline, "timeline").ok
contracts = ti.visualization_contracts(timeline=timeline, evolution=evo, analytics=analytics)
```

Run the tests: `pytest tests/test_temporal_intelligence.py`.
See [`docs/V3_P2_TEMPORAL_INTELLIGENCE.md`](./docs/V3_P2_TEMPORAL_INTELLIGENCE.md).

## Scope guard (NOT built — NR-13)
No knowledge graph, operational analytics/recommendations/**dashboards** (only viz
contracts), FHIR/HL7/EMR, realtime streaming, or V4 features.
