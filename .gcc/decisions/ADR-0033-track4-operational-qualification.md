# ADR-0033 — Track 4: Operational Readiness & Deployment Qualification Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Product Completion Program — Track 4 (Operational Readiness & Deployment Qualification)
> **Builds on:** ADR-0001 … ADR-0032 (Productization P1–P10 + DRP-1…DRP-6 + Track 1 + Track 2 + Track 3)
> **Resolves:** Production Reality Audit blocker — *NO DEPLOYMENT QUALIFICATION*
> (operational readiness, deployment readiness, observability, and qualification evidence insufficient)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems), AP-9/NR-5 (this record),
> NR-13 (scope), NR-2 (honesty)

## 1. Context

Track 3 delivered a **usable product** (READY_FOR_USERS): a real FastAPI API + upload →
prediction → report workflow over real EEG + real models. The audit's next blocker is *no
deployment qualification*: insufficient operational readiness, deployment readiness,
observability, and qualification evidence.

Track 4 closes that blocker by turning the usable product into a **deployable product**: it
qualifies operations — health monitoring, operational monitoring, diagnostics, deployment
qualification, and operational readiness (NOT_READY / PARTIALLY_READY / READY_FOR_DEPLOYMENT)
— over the real Track-3 product. Scope is strictly operational readiness — no retraining, no
dataset changes, no Track 1/2/3 workflow changes, no prediction-logic changes, no security
changes (NR-13), and no new AI system / architecture.

## 2. Decisions

### D1 — A new governed `backend/operations_platform` subsystem (observe-only)
It mirrors the platform subsystem shape (models, identity, health, monitoring, diagnostics,
qualification, readiness, registry, audit, lineage, reports, schemas, service). It **observes**
the Track-3 `ApplicationPlatformService` **read-only** — it constructs nothing in the product
and re-runs no business logic; it inspects already-produced state and exercises read-only
paths. As a `backend` package it obeys the import DAG (imports `ml` + sibling `backend`, never
`frontend`; enforced by `tests/test_boundaries.py`). It is distinct from the top-level P8
`operations/` ops layer; Track 4 is an in-DAG governed qualification subsystem.

### D2 — Health (T4-B) / Monitoring (T4-C) / Diagnostics (T4-D) over the real product
- **Health:** seven components (service / dataset / model / storage / API / workflow /
  prediction) → HEALTHY / DEGRADED / UNHEALTHY, aggregated to an overall state.
- **Monitoring:** request / prediction / upload volume + failures + validation errors
  (deterministic counts), plus latency / processing-time / resource (informational).
- **Diagnostics:** workflow / prediction / upload / API / failure domains with a closed
  **root-cause** vocabulary (missing_model / missing_dataset / invalid_upload /
  corrupted_state / api_error / workflow_incomplete / …); structured findings, never raises.

### D3 — Deployment qualification (T4-E) + readiness (T4-F)
- **Qualification** validates the availability of dataset / model / API / workflow / report /
  persistence / security → QUALIFIED / CONDITIONALLY_QUALIFIED / NOT_QUALIFIED (model/API/
  workflow/report/dataset are blocking; persistence/security are warning-level).
- **Readiness** combines seven weighted dimensions (operational / monitoring / health /
  qualification / registry / audit / lineage) → **NOT_READY / PARTIALLY_READY /
  READY_FOR_DEPLOYMENT**. `READY_FOR_DEPLOYMENT` requires HEALTHY + monitoring active +
  diagnostics pass + QUALIFIED + registered + audited + traceable.

### D4 — Reuse the shared lineage + audit (T4-G; no parallel systems)
All nodes are recorded in the **product's** `ml.lineage` tracker (shared), and events on the
shared `ImmutableAuditLog`. The health-event node parents the observed Track-3 workflow node
(which chains back through Prediction → Model → Recording → Dataset), and the
qualification-event node parents the health-event node — realizing **Dataset → Model →
Prediction → Workflow → Health Event → Qualification Event**; one `verify_chain` from a
readiness node reaches the dataset + model.

### D5 — Determinism (NR-9/NR-10)
Ids/fingerprints are content-addressed over the observed deterministic state; wall-clock
latency / processing-time / resource measures are informational and excluded from every
signature **and** from the deterministic reports (the monitoring report lists the names of
the informational measures tracked, not their volatile values). The same observed product
reproduces the same health/qualification/readiness ids + byte-identical reports.

## 3. Consequences

- `python -m scripts.verify_track4_operations` → **ALL 15 CRITERIA PASS** against the real
  Track-3 product over the real CHB-MIT corpus: health HEALTHY (7/7), monitoring active,
  diagnostics pass, qualification QUALIFIED (7/7), **READY_FOR_DEPLOYMENT** (score 1.0),
  operational lineage verified to the product workflow, audit verified, registry orphan-free.
- New suite adds **18 tests**; full repository suite **1027 passed** (was 1009). Tests run
  **network-free** (real Track-3 product over committed real EDF fixtures); a real-corpus test
  runs over the genuine PhysioNet recordings when available.
- `ruff` clean on all new code; `tests/test_boundaries.py` green; prior verify scripts
  (Track 1, Track 2, Track 3, DRP-1…DRP-6, productization) unaffected. No new dependencies.

## 4. Scope guard (explicitly NOT built — NR-13)

Model retraining, dataset changes, Track 1/2/3 workflow changes, prediction-logic changes,
security-architecture changes, deployment-infrastructure changes, new AI systems / new
architecture. Track 4 qualifies operations — **only**; it alters no business logic.

## 5. Honesty statement (NR-2)

Track 4 delivers **real operational qualification evidence**: health, monitoring, diagnostics,
deployment qualification, and a deployment-readiness verdict computed from the real observed
product, with complete traceability + tamper-evident audit. `READY_FOR_DEPLOYMENT` certifies
that the in-repo product is **operationally qualified** — observable, diagnosable, qualified,
and traceable — **not** that a production cluster is provisioned. Actual production hosting
(TLS termination, autoscaling, secrets management, multi-node orchestration) remains a
deployment-infrastructure concern, explicitly out of scope. The health/qualification verdicts
reflect the real in-process product on the real single-subject cohort (Tracks 1–3 honesty
carries forward). This closes the *no deployment qualification* blocker: NeuroVision can now
monitor health, monitor operations, diagnose failures, qualify deployments, score readiness,
track operational lineage, and produce deployment evidence using the existing application
platform.
