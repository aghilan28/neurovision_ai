# V3-P1 — Operational Event Foundation

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0007](../../../.gcc/decisions/ADR-0007-v3-p1-p2-events-and-temporal.md)

Events become first-class platform entities — permanent, immutable facts about
meaningful changes.

## 1. What/when/why/how (the V3 questions)
Each event answers: **what** happened (event type), **when** (the deterministic
logical clock), **why** (the source audit entry + summary it was observed from),
and **how it relates** (relationships → causal/sequence/dependency chains).

## 2. Observe, don't own (the integration model)
```
V2 subsystem audit log (immutable, hash-chained)         e.g. CaseService.audit_log_for(case_id)
        │  (read-only)
        ▼
generation/adapters.<Kind>EventAdapter.observe_log(...)  maps audit kind -> taxonomy event type
        │
        ▼
OperationalEventService.record_event(...)                gate -> lineage -> audit -> version -> registry
        │
        ▼
EventRecord (immutable fact)  +  EventRelationship(s)     parented by the source entity lineage node
```
The adapters never modify the systems they observe; the source audit log entry's
`event_hash` is pinned in the event's metadata (proof the event is observed, not
invented).

## 3. Determinism: the logical clock
`LogicalClock = (ingestion_ordinal, source_seq, epoch)`. No wall-clock enters any
hashed payload (NR-9/NR-10). The event id is
`event+sha16(type, category, source_entity_id, source_version, clock)`, so the same
source fact always mints the same event, and a different occurrence mints a
different one.

## 4. Immutability & supersession
An event is born `active` and may only transition to `superseded`. Supersession
records a **new** event (with `supersedes=<old id>`), adds a `supersedes`
relationship, and flips the old event's registry status to `superseded` — a
governed, audited change that **never rewrites** the original fact.

## 5. Validation (8 dimensions)
identity · registry · audit · lineage · relationship · version · taxonomy ·
immutability. The governance gate (architecture/quality/context/risk) runs before
registry admission; "risk" here means *the event is anchored to a source audit
entry* (it cannot be invented).

## 6. Lineage
Each event node's parent is the observed source entity's lineage node, so
`verify_chain(event.lineage_id)` reaches **Patient → … → Event**.

## 7. Scope guard (NOT built)
No analytics/recommendations/dashboards (V3-P2+ / forbidden), no knowledge graph,
no FHIR/HL7/EMR, no realtime, no V4.
