# `backend/` — Application Layer

> **Layer:** Application Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-4 (preserve uncertainty), AP-5/AP-8 (traceability/auditability), AP-7 (boundaries), NR-4, NR-11, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The **orchestration and service** layer. It composes the domain modules
(`ml`, `evaluation`, `datasets`, `preprocessing`) into application services and
exposes them via APIs to the presentation layer — **preserving uncertainty and
provenance** end-to-end.

---

## Purpose
Provide application services and APIs that orchestrate domain logic and deliver
**traceable, uncertainty-bearing** results to the frontend.

## Responsibilities
- Orchestrate domain modules into use cases (e.g. "process recording → detect →
  attach uncertainty → record provenance").
- Expose **API contracts** to `frontend/` (the frontend talks only to the backend).
- **Preserve** uncertainty produced by `ml/` without flattening it (AP-4, NR-4).
- Maintain the **audit trail / provenance** for every clinical output (AP-5/AP-8, NR-11).
- Enforce that clinical outputs are traceable to input + preprocessing version +
  model version + uncertainty.

## Allowed dependencies
- ✅ `ml/`, `evaluation/`, `datasets/`, `preprocessing/`.
- ✅ Pinned third-party service/web/storage libraries.

## Forbidden dependencies
- ❌ `frontend/` — the dependency is one-way: **frontend depends on backend, never
  the reverse** (NR-8).
- ❌ `deployment/`, `monitoring/` as code imports — backend emits telemetry; it
  does not import the infrastructure that observes it.
- ❌ Dropping/altering uncertainty (NR-4) or producing untraceable outputs (NR-11).

## Future responsibilities
- **V2:** clinical-workflow services, API contracts, audit-trail implementation.
- **V3:** near-real-time ingestion/inference orchestration.
- **V4:** hospital-grade service hardening (security, reliability) for deployment.

## Version ownership
- **Introduced/owned from V2.** Contract defined in **V0-P2** (this README).

## Examples
- A service that accepts a recording reference, runs the `ml` inference path, and
  returns detections **with** their uncertainty and provenance.
- An API endpoint returning a prioritized review queue for clinicians (V2).
- An audit-record writer that logs the lineage of every served result.

## Boundary rules
- May import all domain modules (`ml`, `evaluation`, `datasets`, `preprocessing`);
  must **not** import `frontend/` (see the acyclic
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Communicates with `frontend/` **only via defined API contracts**, never by
  sharing internal code.
- Must **preserve** uncertainty and provenance; it may not collapse a prediction
  set to a bare label.
- Does not implement DSP (`preprocessing/`), modeling (`ml/`), or metric
  computation (`evaluation/`) itself — it orchestrates them.
