# `backend/` — Application Layer

> **Layer:** Application Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined.
> **Status (V1-P7):** **Offline implementation present** — `offline_inference/` (see "V1 Offline Implementation" below). Clinical/API/deployment remain V2+.
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


---

## V1 Offline Implementation (V1-P7)

> A **governed scope extension**: the directive introduces an *offline* application
> layer in V1. The architecture is **populated, not re-layered** (AP-1). Decision:
> [`../.gcc/decisions/ADR-0002`](../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md).

`backend/offline_inference/` is the **Offline Inference Platform** — a deterministic
15-stage orchestration of every V1 subsystem (raw EEG → registered intelligence
output), with an inference registry, checksummed artifacts, content-addressed
lineage, 7-check validation, six reports, and a recoverable job system.

- **Offline only.** No APIs, networking, real-time, multi-user, or clinical
  deployment (V2+).
- **Boundary.** Imports `ml`/`evaluation`/`datasets`/`preprocessing` and composes
  them; **never** imports `frontend` (enforced by `tests/test_boundaries.py`).
- **Run:** `python -m scripts.run_offline_inference --render-app` ·
  `python -m scripts.verify_v1`.

See [`offline_inference/README.md`](./offline_inference/README.md).


---

## V2 Clinical Workflow (V2-P1 + V2-P2)

> Version 2 models the **clinical workflow** (not deployment/FHIR/EMR/real-time).
> Decision: [`../.gcc/decisions/ADR-0003`](../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md).

The backend gains two clinical subsystems built on the certified V1 platform:

- **`clinical_cases/`** (V2-P1) — the **Case** as the first-class object:
  Patient → Case → Study, with content-addressed identities, an 8-state lifecycle,
  an immutable tamper-evident audit log, a registry, shared lineage, 7-check
  validation, and reports. Links a V1 inference run as a Study.
- **`clinical_review/`** (V2-P2) — structured human **Review**: 8-state workflow,
  sessions, assignment, tracking, registry, audit, lineage, 7-check validation, and
  reports. Shares the case's lineage tracker.

Together they execute the required deliverable with complete traceability:
Patient → Case → Study → Inference Artifacts → Review Session → Review Lifecycle →
Audit Trail → Lineage Trail.

- **Boundary.** Both import `ml` + the sibling clinical subsystem and integrate with
  `offline_inference`; neither imports `frontend`.
- **Run:** `python -m scripts.run_clinical_workflow` · `python -m scripts.verify_v2`.

See [`clinical_cases/README.md`](./clinical_cases/README.md) and
[`clinical_review/README.md`](./clinical_review/README.md).
