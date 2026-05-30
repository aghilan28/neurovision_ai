# `backend/operational_events/` — Operational Event Foundation (V3-P1)

> **Layer:** Application (`backend/`) — a V3 subsystem
> **Status:** Implemented (V3-P1)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9 (versioned decisions), NR-9/NR-10/NR-11; ADR-0007

Introduces **events** as first-class platform entities. Version 2 stored *state*;
Version 3 stores *facts about change*. An event records a meaningful change that
occurred within the system and becomes a **permanent operational record**.

---

## Principles
Every event is **immutable, versioned, traceable, auditable, lineage-tracked,
recoverable, governed**. Events are **facts**: never edited; they may be
**superseded** (a new event references the one it supersedes), never rewritten.

## Events observe; they do not own
Events are **derived** from the immutable Version 2 audit logs by the generation
framework's adapters (`generation/`). The adapters read each subsystem's existing
hash-chained audit log and emit events; **no V0/V1/V2 code is modified**, no
parallel registry/audit/lineage is created. The subsystem shares the platform's
single `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`.

## Time is a deterministic logical clock (NR-9/NR-10)
There is **no wall-clock** anywhere. "When" is a `LogicalClock` —
`(ingestion_ordinal, source_seq, epoch)` — so identical source facts always mint
identical event ids and versions, and replays are byte-identical.

## Domain model
`EventIdentity` · `EventRecord` · `EventMetadata` · `EventType`/`EventCategory`
(taxonomy) · `EventVersion` · `EventAuditRecord` · `EventLineageRecord` ·
`EventRegistryRecord` · `EventRelationship`. Each has a contract in `contracts/`
(Schema · Version · Validation · Audit · Lineage rules).

## Taxonomy (`taxonomy/`)
A closed, versioned vocabulary of categories — case, review, finding, knowledge,
intelligence, decision, system, validation, **governance**, quality — and the
event types permitted in each. Governance/quality/validation actions are
first-class events.

## Relationships (`registry/`)
`observes` (event→source), and `causal` / `sequence` / `depends_on` / `supersedes`
(event→event), supporting causal, dependency, and sequence chains.

## Validation (`validation/`)
Eight integrity dimensions — identity, registry, audit, lineage, relationship,
version, taxonomy, immutability — plus the governance gate (architecture / quality
/ context / risk) every event passes before registry admission.

## Quick start
```python
from backend.operational_events import OperationalEventService
from backend.operational_events.generation import CaseEventAdapter

evs = OperationalEventService(lineage_tracker=case_service.lineage)
events = CaseEventAdapter(evs).observe_log(
    source_entity_id=case.case_id, source_version=case_service.registry.get(case.case_id).version,
    audit_log=case_service.audit_log_for(case.case_id), source_lineage_id=case.lineage_id,
    ingestion_ordinal=0, created_at="1970-01-01T00:00:00Z")
assert evs.validate(events[0]).ok
```

Run the tests: `pytest tests/test_operational_events.py`.
See [`docs/V3_P1_OPERATIONAL_EVENTS.md`](./docs/V3_P1_OPERATIONAL_EVENTS.md).

## Scope guard (NOT built — NR-13)
No knowledge graph, operational analytics/recommendations/dashboards, FHIR/HL7/EMR,
hospital integration, realtime streaming, or V4 features.
