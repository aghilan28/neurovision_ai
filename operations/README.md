# Operations Foundation Platform (`operations/`) — Productization P8

Transforms the **usable product** (P1–P7) into a **deployable product**. The objective is
operational readiness — *nothing else*. No model/inference changes, no frontend/backend
redesign. This is the top-level **operationalization** layer (peer of `scripts/`): it
**composes and observes** the existing systems and modifies none of their workflows.

```
Build → Deploy → Monitor → Log → Recover → Validate   (without manual intervention)
```

## Where it sits (and why it may import backend/frontend)

`operations/` is **not** one of the six governed domain packages, so the architecture
boundary tests do not constrain it (exactly like `scripts/`). It may import `backend`
and `frontend` — and does so **lazily, inside functions** — to run real health checks,
back up real registries, and smoke the real pipeline. The dependency is one-way: **no
domain package imports `operations`** (asserted by `tests/test_operations.py`).

## Layout (P8-A)

```
operations/
  version.py / util.py / cli.py        # versions, deterministic helpers, the ops CLI
  config/        # P8-D: ConfigLoader, ConfigValidator, SecretsProvider (no hardcoded secrets)
  environments/  # P8-B: dev/testing/staging/production specs + *.env.template (no real secrets)
  deployment/    # P8-C: Dockerfile.backend, Dockerfile.frontend, compose + static validators
  health/        # P8-E: liveness/readiness + backend/frontend/model/storage/workflow/system
  logging/       # P8-F: deterministic structured (JSON) logging + correlation
  monitoring/    # P8-G: in-process metrics registry + report (no cloud)
  backups/       # P8-H: checksummed registry/config/artifact backups
  recovery/      # P8-H: restore + verified recovery (tamper-detecting)
  ci/            # P8-I: repository-native pipeline (build/lint/test/verify) + quality gate
  validation/    # P8-J: 8 operations-integrity checks
  reports/       # P8-K: 8 operational reports + the Operations Readiness verdict
  docs/          # DESIGN.md, DECISIONS.md, RUNBOOK.md
  tests/         # pointer to repository-root tests
```

## Containerization (P8-C)

Real, reproducible images (build context = repository root):

```bash
docker build -f operations/deployment/docker/Dockerfile.frontend -t neurovision-frontend .
docker build -f operations/deployment/docker/Dockerfile.backend  -t neurovision-backend  .
```

* **frontend image** — slim, **stdlib-only** (presentation layer); builds in seconds, its
  start command renders the login page (`FRONTEND_OK`), its healthcheck is
  `operations.cli live`.
* **backend image** — the full P1–P7 platform + pinned deps; healthcheck `operations.cli
  live`, start command runs the operational health set.
* **compose** (`compose/docker-compose.yml`) — both services, shared config via
  `env_file`, a persistent `nv_data` volume, healthchecks. Secrets are never inline.

> Sandbox note: the runtime is Podman/Buildah with **no `docker compose` provider**, so
> the compose file is validated **structurally** (`operations.deployment.validate_compose`)
> while `docker build`/`docker run` of the slim frontend image is exercised **for real**
> by `scripts/verify_productization_p8`.

## Configuration & secrets (P8-D)

Config is loaded from a `NV_`-prefixed environment over per-environment defaults. Secrets
resolve through a `SecretsProvider` (env var or mounted file) — **never hardcoded** — and
are always **redacted** in any serialized config/report/backup. Real environments reject
placeholder/empty secrets.

## The operations CLI

```bash
python -m operations.cli live                  # liveness (slim-safe; container healthcheck)
python -m operations.cli ready  --environment testing
python -m operations.cli health --environment testing
python -m operations.cli config --environment production
python -m operations.cli backup --dest ./bk --environment testing
python -m operations.cli restore --dest ./bk
python -m operations.cli validate
python -m operations.cli report
```

## Verify

```bash
python -m scripts.verify_productization_p8     # all 15 phase-completion criteria
python -m pytest tests/test_operations.py
```

## Determinism

Config signatures, log records, metrics, backup manifests, and reports are all
deterministic (no wall-clock, no randomness) for a given input. See
`.gcc/decisions/ADR-0021-productization-p8-operations-foundation.md`.
