# ADR-0034 — DBE-1: ASGI Entrypoint & Server Startup Fix

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Blocker Elimination Program — DBE-1
> **Builds on:** ADR-0001 … ADR-0033 (Productization + DRP + Tracks 1-4)
> **Resolves:** Final Hostile QA Audit CRITICAL blocker — *NO RUNNABLE HTTP SERVER ENTRYPOINT*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-7/NR-8 (boundaries),
> AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

The Final Hostile QA Audit confirmed the Track-3 FastAPI application works in-process but
found a CRITICAL deployment blocker: **there was no runnable HTTP server entrypoint.**
`create_app(service)` built the app, but nothing launched it — no `uvicorn.run`, no
module-level `app`, no `__main__`. An independent operator could not start NeuroVision as a
running HTTP service.

DBE-1 resolves **only** that blocker. Scope is strictly server startup — no changes to
datasets, models, inference, persistence, security, operations, Track 1-4, Docker, deployment
infrastructure, the duplicate-upload bug, or token handling (all explicitly forbidden here and
deferred to their own DBE phases).

## 2. Decisions

### D1 — A single authoritative ASGI entrypoint: `backend.application_platform.server.app:app`
A new `backend/application_platform/server/` package exposes a module-level `app` (the real
Track-3 FastAPI application). This is the **only** production bootstrap — there is no
alternative startup path and no duplicated initialization. Importing the module constructs the
app once, per the standard `uvicorn module:app` convention.

### D2 — An application factory using **real** production construction (DBE1-C)
`factory.build_application(config)` constructs the real `ApplicationPlatformService` (which
already wires the reused `application_backend` → P1-P5 + model foundation + auth/security over
the shared `ml.lineage` tracker + shared `ImmutableAuditLog`) and the real Track-3 app via the
existing `create_app(service)`. No mock services, no simplified paths, no bypass. The factory
is the single construction path shared by every startup route.

### D3 — Typed, validated, env-driven startup configuration (DBE1-D)
`config.ServerConfig` + `load_config()` read `NV_*` env vars (host / port / environment /
log level / reload / workspace dir / analysis seconds) with documented defaults and fail-fast
validation (`StartupConfigError`). No hidden configuration. Deterministic: identical inputs →
identical config. Production forces `reload=False` (one authoritative, stable process).

### D4 — Application lifespan: startup validation + graceful shutdown (DBE1-F/G)
The app's lifespan runs startup validation (health / readiness / security / operations
constructible) and records `app.state.startup_report`; a failed validation **raises** (no
silent partial start). Shutdown releases in-memory references idempotently and never raises.
Two operational probes are added — `/livez` (liveness) and `/readyz` (readiness, gated on the
startup report) — alongside the existing `/health`.

### D5 — Both launch paths serve the same app (DBE1-E)
`uvicorn backend.application_platform.server.app:app` and
`python -m backend.application_platform.server.app` launch the **same** `app` object through
the **same** factory. The module path's `run()` uses uvicorn; in reload mode it passes the
import string (which resolves to this very `app`), so there is no duplicated init.

## 3. Consequences

- `python -m scripts.verify_dbe1_asgi_entrypoint` → **ALL 15 CRITERIA PASS**, including a
  **real bounded uvicorn subprocess** that served a live HTTP socket (`/health`, `/livez`,
  `/readyz`, `/v1/readiness`, `/openapi.json`, a real auth round-trip) and **shut down
  gracefully on SIGTERM** (rc=-15), plus the `python -m` module path serving live HTTP.
- New suite adds **15 tests** (`tests/test_server_entrypoint.py`), incl. a real uvicorn
  subprocess launch; full repository suite **1042 passed** (was 1027).
- `ruff` clean on all new code; `tests/test_boundaries.py` green; no prior verify script or
  business logic touched. No new dependencies (uvicorn was already pinned in Track 3).
- Operator/developer/production startup guides with exact commands in
  `backend/application_platform/server/README.md`.

## 4. Scope guard (explicitly NOT done — NR-13)

Did not fix the duplicate-upload 500, persistence wiring, or invalid-token 500; did not modify
Docker/deployment assets, models, datasets, inference, security, operations, or Track 1-4.
Those remain open audit findings for their own DBE phases.

## 5. Honesty statement (NR-2)

DBE-1 makes the existing Track-3 API **launchable as a real HTTP service** — verified by
starting and stopping an actual uvicorn process and exercising the live socket. It changes no
business logic. The other audit-identified blockers (duplicate-upload 500, unwired
persistence → state lost on restart, invalid-token 500, Dockerfile still running the P8 ops
CLI rather than serving this app) are **still open** and out of scope here; this ADR closes
only the "no runnable HTTP server entrypoint" blocker. A running server now exists; full
operator-deployable readiness still depends on the remaining DBE phases.
