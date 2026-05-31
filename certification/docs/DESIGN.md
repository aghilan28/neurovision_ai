# Deployment Readiness & Production Certification — Design (Productization P10)

## Objective

Render an honest, evidence-based deployment verdict for NeuroVision by auditing the real
P1–P9 systems. Certification only — it modifies nothing and adds no capability.

## Position

`certification/` is a top-level certification layer (peer of `scripts/`/`operations/`/
`validation/`). It audits and observes; it is unconstrained by the per-module import DAG and
imports `backend`/`operations`/`validation` lazily. One-way: no domain package imports it.

## Single evidence bundle

`EvidenceCollector` runs the platform **once** and assembles every fact the certification
rests on: the P9 validation program, the end-to-end journey (P10-D), the P8 operations
health/validation/deployment/config, and platform compliance (determinism / traceability /
boundaries / governance / NR-4). All audits, scorecards, risk, gap, and the decision consume
this one bundle — so they cannot disagree about the facts.

## Audits

* **Product readiness (P10-B)** — per-phase operational/validation/readiness/gap states +
  readiness/risk/gap/evidence findings, derived in `readiness/`.
* **End-to-end (P10-D)** — the full real journey (login → … → reports + monitoring +
  recovery), 10 certified checks.
* **Deployment readiness (P10-C)** — build/deploy/config/recovery/monitoring/operational/
  security readiness from the operations evidence.
* **Risk (P10-E)** — a deterministic register across data/model/deployment/security/
  operational categories and CRITICAL/HIGH/MEDIUM/LOW severities, each with a mitigation
  *recommendation* (recommendations only; nothing is implemented).
* **Gap (P10-F)** — what exists/partial/missing, classified, with clinical vs non-clinical
  deployment-blocking flags.

## Scorecards & decision

`scorecards/` produces nine readiness scorecards (measurable boolean criteria; accuracy is
never a gating criterion). `decision.py` applies deterministic rules to the audits to render
exactly one verdict (CERTIFIED / CONDITIONALLY CERTIFIED / NOT CERTIFIED) with a go/no-go
recommendation, scope, conditions, and citations of readiness/risks/gaps/validation/
operations/deployment. The decision is a **pure function of the evidence** — reproducible.

## Why CONDITIONALLY CERTIFIED is the honest verdict

The technical foundation is fully met (end-to-end 10/10, validation complete, operations
green, deterministic, traceable) and no gap blocks a non-clinical deployment — so it is not
NOT CERTIFIED. But disclosed conditions (synthetic-only data + untuned models G1, in-memory
persistence G3, production security hardening, formal clinical validation) remain — so it is
not unconditionally CERTIFIED. The engine therefore returns CONDITIONALLY CERTIFIED with the
conditions enumerated, exactly as the evidence dictates.

## Out of scope (forbidden in P10)

New models, model retraining, frontend/backend/infrastructure/deployment/monitoring/security
changes, Version 5, any new productization phase. Certification evaluates; it never modifies.
