# ADR-0035 — DBE-2: Docker Deployment & Container Startup Fix

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Blocker Elimination Program — DBE-2
> **Builds on:** ADR-0001 … ADR-0034 (Productization + DRP + Tracks 1-4 + DBE-1)
> **Resolves:** Final Hostile QA Audit CRITICAL blocker — *DOCKER DEPLOYMENT DOES NOT SERVE THE PRODUCT*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-7/NR-8 (boundaries),
> AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

The Final Hostile QA Audit found that the deployment assets predate Track 3: the backend
Dockerfile `CMD` ran `python -m operations.cli health` (a one-shot health report that exits),
the `HEALTHCHECK` ran `operations.cli live` (exec-style, not HTTP), and the compose backend
service published **no port** with `restart: "no"`. So `docker compose up` ran a health check
and exited — it never served the API. DBE-1 then added a real ASGI entrypoint
(`backend.application_platform.server.app:app`) runnable via uvicorn, but the deployment
assets still didn't use it.

DBE-2 resolves **only** that blocker: the deployment assets must launch the real API. Scope is
strictly deployment assets — no changes to datasets, models, inference, persistence, security,
operations logic, application logic, Track 1-4, the duplicate-upload bug, or token handling.

## 2. Decisions

### D1 — Backend Dockerfile serves the DBE-1 ASGI app via uvicorn (DBE2-B)
`Dockerfile.backend` `CMD` is now
`python -m uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000`
(exec form, so signals reach the process and `docker stop`/SIGTERM triggers the application
lifespan's graceful shutdown). It reuses the **single authoritative DBE-1 entrypoint** — no
duplicated startup logic. The image `EXPOSE`s 8000 and sets production `NV_*` defaults.

### D2 — Real HTTP healthcheck (DBE2-B/D)
A new stdlib-only `operations/deployment/docker/healthcheck.py` performs an HTTP GET against
the running API and exits 0 only on a 2xx. The Dockerfile `HEALTHCHECK` and the compose
`healthcheck:` both use it (probing `/health`), with a `start_period` to allow startup. The
container is reported healthy only when it is **actually serving HTTP** — not merely alive.

### D3 — Compose launches + keeps the API (DBE2-C/F)
`docker-compose.yml` backend service now runs the same uvicorn `command`, **publishes
`8000:8000`**, injects `NV_*` env + the `env_file`, uses the HTTP `healthcheck`, and sets
`restart: unless-stopped`. The frontend `depends_on` the backend `service_healthy`. So
`docker compose up` yields a running, health-gated API reachable on port 8000.

### D4 — Honest, runtime-free verification (DBE2-D/E/G/J)
This sandbox has no container runtime (Podman/Buildah, no `docker compose` provider — the same
condition P8 documented). DBE-2 therefore validates the container *definitions* structurally
**and** proves the **exact container start command** serves live HTTP by launching it directly
(a bounded uvicorn subprocess built from the same argv the Dockerfile/compose `CMD` use), then
stopping it gracefully (SIGTERM). On a host with Docker the identical command runs inside the
container.

### D5 — Operations logic untouched
The shared `operations/deployment/__init__.py` validator (which P8 depends on) is **not**
modified. DBE-2's own verify script + tests assert the new API-serving invariants directly.
The new `healthcheck.py` is a deployment *asset*, not operations logic.

## 3. Consequences

- `python -m scripts.verify_dbe2_docker_deployment` → **ALL 15 CRITERIA PASS**: the backend
  Dockerfile + compose serve the uvicorn ASGI app, expose the port, and use an HTTP
  healthcheck; the exact container start command served live HTTP (`/health`, `/readyz`,
  `/v1/readiness`, `/openapi.json`) and shut down gracefully; the healthcheck script passes up
  and fails down.
- New suite `tests/test_docker_deployment.py` (12 tests) validates the assets + a real launch;
  full repository suite remains green.
- `ruff` clean; `tests/test_boundaries.py` green; no prior verify script, business logic, or
  operations logic touched. No new dependencies (uvicorn/fastapi pinned since Track 3).
- Operator/Docker/Compose/Validation guides with exact commands in `deployment/README.md`.

## 4. Scope guard (explicitly NOT done — NR-13)

Did not fix the duplicate-upload 500, persistence wiring, or invalid-token 500; did not modify
datasets, models, inference, security/operations/application logic, or Track 1-4. Those remain
open audit findings for their own DBE phases.

## 5. Honesty statement (NR-2)

DBE-2 makes `docker compose up` (and `docker run`) **serve the real NeuroVision API** instead
of running a one-shot health check — verified by launching the exact container start command
and exercising the live HTTP socket, then stopping it gracefully. Because the sandbox has no
container engine, the image is not built here; the *definitions* are validated structurally
and the *start command* is proven live (the same honest strategy P8 used for the slim image).
The other audit-identified blockers (duplicate-upload 500, unwired persistence → state lost on
restart, invalid-token 500) are **still open** and out of scope here; this ADR closes only the
"Docker deployment does not serve the product" blocker.
