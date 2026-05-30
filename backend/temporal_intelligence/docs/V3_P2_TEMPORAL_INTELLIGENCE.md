# V3-P2 — Temporal Intelligence Layer

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0007](../../../.gcc/decisions/ADR-0007-v3-p1-p2-events-and-temporal.md)

Teaches the platform about time: state evolution, history, progression, and
operational timelines — all derived from events.

## 1. Data flow (derived strictly from events)
```
OperationalEventService (V3-P1)  ──▶ EventRecord[]  ──load_events──▶ EventSourceView (deterministic order)
                                                                          │
        ┌───────────────────────────┬───────────────────────────┬───────┴───────────┐
        ▼                           ▼                           ▼                   ▼
  TimelineEngine             HistoryEngine             EvolutionEngine     TemporalAnalyticsEngine
   Timeline                    History                  EvolutionRecord       TemporalAnalytics
        └───────────── governance gate ▶ lineage(parents=event nodes) ▶ audit ▶ version ▶ registry ─────────┘
                                                          │
                                                          ▼
                                       schemas.visualization  (contracts only; no UI)
```
The `EventSourceView` orders events by `(ingestion_ordinal, source_seq, epoch,
event_id)` — the events' deterministic logical clock — so every artifact is
reproducible. There is **no hidden state reconstruction**: only recorded events are
read.

## 2. Artifact families
- **Timeline** — ordered `TimelinePoint`s (references to events) for a subject or
  the whole platform (`operational:all`).
- **History** — ordered `HistoryEntry`s carrying each step's source version
  (recoverable version history).
- **EvolutionRecord** — ordered `EvolutionStep`s (`from_state`→`to_state`) inferred
  from lifecycle event types; continuity is validated.
- **TemporalAnalytics** — `DurationMetric`s in **logical steps** (event-count spans;
  unobserved ⇒ `-1`) plus event-type counts.

## 3. Durations without a clock
Because wall-clock is forbidden (NR-9/NR-10), a duration is the number of ordered
operational steps between a start and end event type for a subject, averaged
deterministically across subjects. This is a reproducible *logical* interval, not a
physical time.

## 4. Visualization contracts (no UI)
`timeline_contract`, `event_sequence_contract`, `evolution_graph_contract`,
`duration_graph_contract`, `trend_graph_contract`, `operational_dashboard_contract`
— JSON-able specs a future presentation layer can render. No rendering is done here.

## 5. Lineage & validation
Each temporal artifact's lineage parents are the **event** nodes it derives from,
so `verify_chain` spans Patient → … → Event → Temporal artifact. Validation covers
identity/registry/audit/lineage/version + per-family structural integrity; the
governance gate's "risk" dimension enforces *derived-from-events*.

## 6. Scope guard (NOT built)
No knowledge graph, no operational analytics/recommendations/**dashboards** (only
contracts), no FHIR/HL7/EMR, no realtime, no V4.
