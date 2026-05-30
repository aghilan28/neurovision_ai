# ADR-0021 — Productization P8: Operations Foundation Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P8
> **Builds on:** ADR-0001 … ADR-0020 (esp. P6 ADR-0019 backend, P7 ADR-0020 frontend)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism/reproducibility), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-2 (zero hidden debt), NR-13 (scope)
> **Decision owner:** Platform/operations engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P8 **Operations Foundation Platform** (`operations/`) is
shaped as it is, so the rationale survives turnover (NR-14).

---

## 1. Context

P1–P7 produced a usable product (a real frontend over a governed backend over the EEG →
prediction pipeline). P8 makes it **deployable**: runtime environments, containers,
configuration/secrets management, health/readiness, structured logging, metrics,
backup/recovery, a CI pipeline, operations validation, and operational reporting. The
scope is **operationalization only** — no model/inference changes, no frontend/backend
redesign (NR-13).

## 2. Decisions

### D1 — A top-level `operations/` layer (peer of `scripts/`)
Operations is the operationalization layer that **composes and observes** P1–P7. It is not
one of the six governed domain packages, so the per-module import DAG does not constrain
it; it may import `backend`/`frontend` (lazily, inside functions) to run real health
checks, back up real registries, and smoke the real pipeline. The dependency is strictly
one-way — **no domain package imports `operations`** (asserted in tests). The governed DAG
and all prior phases are untouched.

### D2 — Real container builds where possible; structural validation where not
The sandbox runtime is Podman/Buildah with **no `docker compose` provider**. Therefore the
slim, stdlib-only **frontend** image is built + run **for real** (fast, deterministic;
its start command renders the login page and reports `FRONTEND_OK`), while the full-deps
**backend** image and the **compose** file are validated **structurally**. All are
faithful, runnable definitions with pinned base images, copied code, healthchecks, start
commands, and no baked/inline secrets.

### D3 — No HTTP serving transport is added
A long-running server would be a new backend feature (forbidden). The deployable unit is a
CLI/batch application; container **liveness/readiness** are exposed via `operations.cli`
(the standard exec-style container healthcheck). An HTTP transport is deferred to a later
phase (recorded, not hidden).

### D4 — Secrets are injected, redacted, and never persisted
Configuration resolves secrets through an injectable `SecretsProvider` (env var or a
mounted secrets file) — never hardcoded. Secrets are redacted in every serialized
config/report and excluded from backups; real (staging/production) environments reject
placeholder/empty secrets. The `*.env.template` files contain no real secrets.

### D5 — Determinism preserved (NR-9/NR-10)
Config signatures, structured logs, metrics, backup manifests, and reports are
deterministic for a given input. Structured logs default to a fixed deterministic epoch
clock (a real deployment injects a wall-clock); no randomness enters any artifact.

### D6 — Recovery is verified, not assumed
Restore re-hashes every backed-up component against the checksummed manifest (fails closed
on tampering), reloads the registry defensively (a corrupted file surfaces as a failed
check, never an exception), and asserts the restored registry is orphan-free and
secret-free.

### D7 — CI is repository-native / vendor-neutral
The pipeline runs plain in-repo commands (compile / ruff / pytest / verify) with a quality
gate and a release validator; it can be wired into any CI provider but locks into none.

## 3. Consequences

- `python -m scripts.verify_productization_p8` exercises all 15 criteria (**ALL PASS**),
  including a **real** frontend image build + container run, tamper-detecting recovery, the
  CI quality gate, and a deployable upload→prediction smoke.
- The new suite adds 20 tests; the full repository suite is **810 passed** (was 790).
  `ruff` is clean on all new code; `tests/test_boundaries.py` stays green; no domain
  package imports `operations`.
- No new runtime dependencies; the frontend image is stdlib-only.

## 4. Scope guard (explicitly NOT built — NR-13)

New models, new inference, new frontend/backend features, clinical validation, benchmark
programs, pilot deployments, Productization P9+, and Version 5.

## 5. Inherited gaps / follow-ups (NR-2)

- **G3 (in-memory persistence):** backups snapshot the in-memory registry + on-disk
  content-addressed stores; durable databases remain out of scope.
- A long-running HTTP serving transport + an orchestrator manifest (k8s) over the same
  images/CLI are deferred to a later phase.
- The legacy V0 `deployment/` and `monitoring/` placeholder directories remain as-is; the
  operational implementation lives under `operations/` per this phase's directive.
