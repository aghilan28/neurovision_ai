# Operations Foundation Platform — Design (Productization P8)

## Objective

Make the P1–P7 product **deployable**: runtime environments, containers, configuration,
health/readiness, logging, metrics, backup/recovery, CI, validation, and reporting — with
**no** change to any AI/backend/frontend workflow.

## Position in the architecture

`operations/` is a top-level operationalization layer (peer of `scripts/`). It composes
and observes the platform. It is unconstrained by the per-module import DAG (it is not one
of the six governed packages), so it may import `backend`/`frontend` — lazily, inside
functions — to exercise the real systems. The dependency is strictly one-way: **no domain
package imports `operations`**.

## Subsystems

* **config (P8-D)** — `ConfigLoader` layers `NV_`-prefixed env over per-environment
  defaults into a typed `AppConfig`; `SecretsProvider` resolves secrets from env or a
  mounted file (never hardcoded); `ConfigValidator` enforces required keys, types, and —
  in real environments — non-placeholder secrets. Secrets are always redacted.
* **environments (P8-B)** — declarative specs for development/testing/staging/production
  (config profile, dependencies, storage, secret *names*, operational requirements) plus
  `*.env.template` files containing no real secrets.
* **deployment (P8-C)** — two Dockerfiles (slim stdlib-only frontend; full-deps backend) +
  a compose file, with static validators enforcing pinned base images, copied code,
  healthchecks, start commands, and no baked/inline secrets.
* **health (P8-E)** — liveness/readiness + backend/frontend/model/storage/workflow/system
  checks that construct and probe the **real** services (read-only/structural), plus an
  opt-in heavy `smoke_pipeline` that runs a real upload→prediction.
* **logging (P8-F)** — deterministic structured JSON logging with request/workflow/
  prediction/error builders and audit/trace correlation.
* **monitoring (P8-G)** — an in-process metrics registry (counters/gauges/observations)
  with application/workflow/prediction/system/health/error families; no cloud.
* **backups + recovery (P8-H)** — checksummed backups of the registry/config/artifacts and
  a **verified** restore that re-hashes every component (tamper-detecting), reloads the
  registry, and asserts it is orphan-free and secret-free.
* **ci (P8-I)** — a repository-native, vendor-neutral pipeline (build/lint/test/verify) +
  quality gate + release validation.
* **validation (P8-J)** — eight operations-integrity checks exercising the above.
* **reports (P8-K)** — eight operational reports + the Operations Readiness verdict.

## Determinism

No wall-clock or randomness enters any reproducible artifact (config signatures, logs,
metrics, manifests, reports). Logs/timestamps use a fixed deterministic epoch by default
(a real deployment injects a wall-clock). This preserves NR-9/NR-10.

## Sandbox reality (honest constraints)

The container runtime is Podman/Buildah; there is **no `docker compose` provider**.
Therefore: `docker build`/`docker run` of the slim frontend image are exercised for real
(fast, deterministic), the backend image + compose are validated structurally, and the
full deployable upload→prediction flow is proven in-process by `smoke_pipeline` + the test
suite. A long-running HTTP serving transport is intentionally **not** added (that would be
a new backend feature, forbidden in P8); the deployable unit is a CLI/batch application
whose health is exposed via `operations.cli` (the container healthcheck command).

## Out of scope (forbidden in P8)

New models, new inference, new frontend/backend features, clinical validation, benchmark
programs, pilot deployments, Productization P9+, Version 5.
