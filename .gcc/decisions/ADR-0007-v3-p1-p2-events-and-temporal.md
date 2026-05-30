# ADR-0007 — V3-P1 Operational Event Foundation + V3-P2 Temporal Intelligence Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V3-P1 + V3-P2
> **Builds on:** ADR-0001…ADR-0006
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V3-P1 Operational Event Foundation and V3-P2 Temporal Intelligence
Layer are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

V2 (certified) understands *current state*. V3 must understand *events, history,
evolution, change, temporal context, operational behavior* — what happened, when,
why, and how it evolved. This must **evolve from** V2, not replace it: no prior
phase is redesigned, no existing lineage/audit/registry is modified or duplicated.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/operational_events` (V3-P1) and `backend/temporal_intelligence` (V3-P2)
populate the existing Application layer. They import `ml` + sibling `backend`
subsystems; they never import `frontend` (enforced by `tests/test_boundaries.py`).
No layer is added or re-drawn.

### D2 — Events are *observed*, never *owned* (no modification of V0/V1/V2)
The generation framework's adapters read each V2 subsystem's **existing immutable
audit log** and emit events; they do not wrap, modify, or own those systems. Each
event pins the source audit entry's `event_hash` in its metadata, proving it was
observed (not invented). This satisfies "events observe systems; events do not own
systems" and "do not modify existing systems".

### D3 — No parallel lineage/audit/registry (NR-8 spirit, directive mandate)
Both subsystems **share** the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog`. Events/temporal artifacts get their own *registries*
(for the new entity kinds), but they do not create a parallel lineage system or a
parallel registry for existing entities, and they never alter existing lineage
semantics.

### D4 — Time is a deterministic logical clock, not wall-clock (NR-9/NR-10)
The constitution forbids wall-clock in reproducible artifacts. "When" is a
`LogicalClock = (ingestion_ordinal, source_seq, epoch)` derived from the source
audit entry; "duration" in temporal analytics is a count of ordered **logical
steps**, not a physical delta. Identical inputs therefore always yield identical
event ids, versions, timelines, and metrics. Alternatives (timestamps) were
rejected as non-reproducible.

### D5 — Events are immutable facts; supersession, never rewrite
An event is born `active` and may only transition to `superseded`. Supersession
records a *new* event (`supersedes=<old>`), adds a `supersedes` relationship, and
flips the old event's registry status — a governed, audited change that never
rewrites the original fact. The tiny lifecycle (`active → superseded`, no return)
mechanizes "events may never be rewritten".

### D6 — Temporal intelligence is derived strictly from events (no hidden state)
Every timeline/history/evolution/analytics artifact is computed from the recorded
events via a deterministically-ordered `EventSourceView`; its lineage parents are
the **event** nodes it derives from. The temporal governance gate's "risk"
dimension fails any artifact not derived from events — mechanizing "no hidden state
reconstruction allowed".

### D7 — Visualization *contracts* only (V3-P2), no UI (NR-13)
V3-P2 emits JSON-able visualization contracts (timeline / event_sequence /
evolution_graph / duration_graph / trend_graph / operational_dashboard) but
implements **no UI** — honoring the forbidden-work list while leaving a clean seam
for a future presentation layer (which, per NR-8, would consume a snapshot).

### D8 — Reuse + tests in top-level `tests/` (ADR-0001 D4)
`ml.provenance.hash_obj`, `ml.lineage`, `ml.validation.ValidationReport`, and the
shared `ImmutableAuditLog` are reused, not reimplemented. Tests live in `tests/`
(`test_operational_events.py`, `test_temporal_intelligence.py`,
`test_v3_p1_p2_e2e.py`); `scripts/verify_v3_p1_p2.py` checks all 20 criteria.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → **Event → Timeline → History →
  Evolution → Temporal Analytics** (`python -m scripts.verify_v3_p1_p2` → all 20
  criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V0/V1/V2 remain intact (events/temporal only *read* them).
  269 tests pass.

## 4. Scope guard (explicitly NOT built — NR-13)

Knowledge graph, operational analytics/recommendations/dashboards (V3-P2 ships only
viz *contracts*), FHIR/HL7/EMR, hospital integration, realtime streaming, and any
V4 feature.

## 5. Follow-ups / recorded debt (NR-2)

- A future presentation layer can surface events/timelines in the Clinical
  Workstation by extending the snapshot builder (no domain import in `frontend`).
- Durable, checksummed persistence for the event/temporal registries (the inherited
  V2 Gap G3) remains the natural next increment.
