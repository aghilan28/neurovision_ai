# ADR-0019 — Productization P6: Application Backend Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P6
> **Builds on:** ADR-0001 … ADR-0018 (esp. P1 ADR-0014 … P5 ADR-0018)
> **Enforces / honors:** AP-1 (vertical population), AP-6/NR-9/NR-10 (determinism/
> reproducibility), NR-4 (calibrated uncertainty surfaced), AP-5/AP-8/NR-11
> (traceability/audit), AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-6 (reuse),
> NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P6 **Application Backend Platform**
(`backend/application_backend`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

P1–P5 took a real EEG file all the way to a validated, immutable **prediction asset**
(prediction + confidence + calibration + explanation), but only as in-process library
calls. P6 takes the next narrow step: expose those capabilities through governed
**application backend services** so a user can *authenticate → upload an EEG → trigger
analysis → retrieve a prediction/confidence/explanation*. The scope is **backend access
and nothing else** — no frontend, deployment, monitoring, or cloud infrastructure.

This is **productization**, not a new version: it must build strictly on P1–P5 and reuse
existing platform patterns (NR-6).

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/application_backend` mirrors the established subsystem shape (models / identity /
auth / users / workflows / api / validation / storage / registry / audit / lineage /
reports / schemas + service). It imports `ml` + sibling `backend` subsystems, never
`frontend` (enforced by `tests/test_boundaries.py` and a targeted package scan).

### D2 — Orchestrate, never re-implement (NR-6, "no parallel pipelines")
`ApplicationBackendService` composes the **reused** `CaseService` + EEG / signal /
feature / model / inference services over a **single shared** `ml.lineage.LineageTracker`
and the shared `ImmutableAuditLog`. `EegWorkflowService` runs the closed ordered stage
set `UPLOAD → VALIDATE → PROCESS → FEATURES → PREDICT → CONFIDENCE → EXPLANATION` by
delegating to those services — it contains **no** EEG/model/inference business logic.

### D3 — In-process versioned API, not a server (NR-13)
The API surface is an in-process, structured, **versioned (`v1`)** request/response
contract layer (`ApplicationAPI` + `ApiRequest`/`ApiResponse`) over a closed
`ApiOperation` set. FastAPI/HTTP/WebSockets/networking/serving infrastructure are
explicitly **out of scope** and belong to a later phase. Every request is authenticated
(if not public), validated (auth / authorization / request-structure / file-structure),
dispatched, and recorded as an immutable, registered request + response.

### D4 — A workflow *join* node realizes the required chain without touching P1–P5
Rather than modifying the P1–P5 lineage (which would violate "do not redesign prior
phases"), P6 adds three new lineage kinds — `user`, `session`, `upload` — and a
`workflow` **join** node that parents both the upload node and the prediction node. One
`verify_chain` from the workflow node then spans the full required chain
`User → Upload → EEG → Processed → Feature → Model → Prediction` (with Case/Patient/
Dataset/Training Run reached via the reused branches), while the clinical chain stays
intact. There is **no parallel audit or lineage system**.

### D5 — Local authentication; secrets quarantined from determinism (P6-C)
Local authentication only (no social login / OAuth). Passwords are PBKDF2-HMAC-SHA256
salted hashes with constant-time verification; sessions store only a token *fingerprint*.
The **only** non-deterministic inputs (salts, tokens) come from an injectable entropy
source — secure (`secrets`) by default, deterministic in tests. Secrets never enter a
content hash, a record, a report, or the audit/lineage trail: `UserRecord` carries no
password/salt, and credentials live in a private credential store. This preserves
platform determinism (NR-9/NR-10) — re-running reproduces the same `prediction_id` and
workflow version — while keeping secure defaults.

### D6 — Single registry, no orphan records (P6-I)
`BackendRegistry` indexes every entity kind (user / session / upload / request /
response / workflow / analysis / api) and **rejects** any entry lacking an audit head or
a lineage node, so every tracked entity is traceable and auditable.

### D7 — Eight-check application integrity validation (P6-K)
`ApplicationIntegrityValidator` reuses `ml.validation.ValidationReport` to produce the
eight checks over a finalized workflow: authentication, session, workflow, api, registry,
audit, lineage, and version integrity.

## 3. Consequences

- The deliverable executes end to end through backend services only: a user
  authenticates, uploads a real EEG file, triggers analysis, and retrieves a prediction +
  confidence + explanation; the workflow is registered, audited, integrity-validated, and
  traced (`verify_chain` proves `User → Upload → … → Prediction`).
- `python -m scripts.verify_productization_p6` exercises all 15 criteria (**ALL PASS**).
  The new suites add 27 tests; the full repository suite is **769 passed** (was 742).
  `ruff` is clean on all new code; `tests/test_boundaries.py` stays green.
- No new runtime dependencies beyond P1–P5 (numpy/scipy/mne already pinned).
- Acyclic DAG preserved; P1–P5 and V0–V4 remain intact (P6 only reuses upstream services
  and extends the shared lineage/audit with application nodes).

## 4. Scope guard (explicitly NOT built — NR-13)

Frontend, React, Next.js, mobile apps, Docker, Kubernetes, cloud deployment, monitoring,
observability, CI/CD, Productization P7+, and Version 5.

## 5. Follow-ups / recorded debt (NR-2)

- Durable persistence for application state (users/sessions/workflows) shares the
  inherited Gap **G3** (in-memory persistence) and is future work behind the same store
  interfaces.
- An HTTP/serving transport (e.g. FastAPI) over the same `ApplicationAPI` contracts, plus
  deployment/monitoring, are deliberately deferred to a later productization phase.
- Token/session expiry is modeled as explicit revocation (no wall-clock per NR-9);
  time-based expiry can attach behind the same `SessionRecord` contract when a governed
  deterministic clock is introduced.
