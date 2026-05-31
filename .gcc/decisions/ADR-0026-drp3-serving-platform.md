# ADR-0026 — DRP-3: Production Serving Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-3 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0025 (Productization P1–P10 + DRP-1 + DRP-2)
> **Resolves:** Audit blocker — *NO SERVING LAYER* (no serving platform / inference service
> boundary / model serving lifecycle / public execution interface)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty),
> NR-4 (faithful uncertainty)

## 1. Context

After DRP-1 (real datasets) and DRP-2 (production-candidate models), the Independent
Production Reality Audit's next gap was the absence of a **serving layer**. DRP-3 adds the
governed serving platform: an inference service boundary, a model serving lifecycle, and an
in-process public execution interface. The scope is strictly serving infrastructure: no
model-architecture / training / frontend / deployment / operations / security / persistence
changes, and no inference-architecture changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/serving_platform` subsystem
Adds the serving engine, routing, prediction service, execution lifecycle, contracts,
validation, registry, readiness, lineage, audit, reports, schemas, and a service hub. It
serves models; it does **not** train them or modify any other subsystem. As a `backend`
package it obeys the import DAG (imports `ml` + sibling `backend`, never `frontend`; enforced
by `tests/test_boundaries.py`).

### D2 — Reuse the inference foundation for execution (no duplicated prediction logic)
The serving engine delegates execution to the reused `InferenceFoundationService`. The
servable catalog holds each already-trained `model_foundation` model record + the feature
assets the inference foundation needs to deterministically reconstruct + verify it. The
serving platform never re-implements prediction, confidence, calibration, or explanation; it
selects and shapes what is delivered (NR-4: confidence + calibration are always delivered with
the label).

### D3 — Reuse the shared registries / lineage / audit; one new serving registry
The underlying model is served from the shared `ModelRegistry`; the single shared
`ml.lineage.LineageTracker` and shared `ImmutableAuditLog` carry serving lineage + audit. Only
the genuinely-new serving artifacts (requests, executions, responses, readiness assessments,
contracts) live in the new `ServingRegistry`. No parallel model / prediction / dataset
registry is created. DRP-1 datasets, DRP-2 production models, and DRP-3 served predictions
coexist on one shared lineage tracker.

### D4 — Model resolution, selection, and version selection
A `ModelRouter` resolves a request's `model_ref` deterministically — by `model_id`, by
`architecture` + explicit `version`, or by `architecture` (latest loaded; `model_id`
tiebreak).

### D5 — A tracked 7-state execution lifecycle
`request_created → request_validated → model_selected → inference_executed →
response_generated → response_delivered → execution_completed`, order-validated. Invalid
requests / missing models are rejected with a structured `Error` contract and audited — never
a crash, and nothing is half-registered (the registry stays orphan-free).

### D6 — Deterministic serving, with a self-reference-free version
Ids and versions are content-addressed, so serving the same request twice is idempotent and
reproduces the same execution id + version. The execution state signature excludes the
`version_integrity` check (a post-build integrity check) to avoid self-reference; version
integrity is asserted by the integrity validator.

### D7 — Serving readiness with a hard gate
Six weighted dimensions (execution / contract / validation / registry / audit / lineage) →
score + findings + NOT_READY / PARTIALLY_READY / READY. `READY` requires requests + responses
+ lifecycle to work, validation to pass, registry + audit + lineage to exist, and a readiness
score to exist.

## 3. Consequences

- `python -m scripts.verify_drp3_serving_platform` → **ALL 15 CRITERIA PASS**; every
  architecture is served end to end (request → select → infer → respond), **READY**, traceable
  (Dataset → Feature → Model → Inference → Serving Request → Serving Execution → Serving
  Response), and audited.
- The new suite adds 19 tests; the full repository suite is **891 passed** (was 872). `ruff`
  clean on all new code; `tests/test_boundaries.py` green; prior verify scripts (incl. drp1,
  drp2, productization_p5) unaffected.
- No new runtime dependencies; the platform runs offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

Frontend changes, model retraining, deployment changes, operations changes, security changes,
persistence changes, clinical validation, inference-architecture changes, DRP-4+. No HTTP /
networking / serving infrastructure beyond the in-process service contracts.

## 5. Honesty statement (NR-2)

DRP-3 adds the serving **boundary, lifecycle, and execution interface** in-process. It does
not add an HTTP/network transport, deployment, or durable persistence (out of scope / later
phases). Served predictions reflect the underlying untuned reference models on synthetic data
(Gap G1); the serving layer faithfully delivers their uncertainty (confidence + calibration),
never a clinical-performance claim.
