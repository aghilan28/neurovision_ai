# NeuroVision HTTP Service — Startup Entrypoint (DBE-1)

This package turns the Track-3 FastAPI **application** into a runnable HTTP **service**. It is
the **single authoritative** ASGI entrypoint; there is no alternative bootstrap.

The ASGI application object is:

```
backend.application_platform.server.app:app
```

It is built by the application factory (`build_application`) from the **real** production
`ApplicationPlatformService` (which reuses the Track-3 → P1-P5 pipeline, the model foundation,
auth/security, the shared lineage tracker, and the shared immutable audit log). No mock
services, no simplified paths.

---

## Operator Startup Guide (exact commands)

Start the server (standard uvicorn, the recommended production path):

```bash
pip install -r requirements.txt
uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000
```

Start the server (module path — same application, same factory):

```bash
NV_HOST=0.0.0.0 NV_PORT=8000 python -m backend.application_platform.server.app
```

Stop the server:

```bash
# graceful shutdown: send SIGTERM (Ctrl-C in the foreground, or:)
kill -TERM <pid>
```

Validate it is running:

```bash
curl http://127.0.0.1:8000/health     # -> {"status":"ok",...}
curl http://127.0.0.1:8000/livez      # liveness  -> {"status":"alive",...}
curl http://127.0.0.1:8000/readyz     # readiness -> {"status":"ready","ready":true,...}
curl http://127.0.0.1:8000/openapi.json   # full API contract
```

Verify the entrypoint end-to-end (starts + stops a real server, checks every criterion):

```bash
python -m scripts.verify_dbe1_asgi_entrypoint
```

---

## Developer Startup Guide

Development mode enables auto-reload (forced **off** in production):

```bash
NV_ENV=development NV_RELOAD=1 NV_LOG_LEVEL=debug \
  uvicorn backend.application_platform.server.app:app --host 127.0.0.1 --port 8000 --reload
```

Drive the app in-process (no socket) for tests:

```python
from fastapi.testclient import TestClient
from backend.application_platform.server import build_application, load_config

service, app = build_application(load_config({}))
with TestClient(app) as client:          # __enter__ runs the startup lifespan
    print(client.get("/health").json())
```

---

## Production Startup Guide

```bash
pip install -r requirements.txt
NV_ENV=production NV_HOST=0.0.0.0 NV_PORT=8000 NV_LOG_LEVEL=info \
  NV_WORKSPACE_DIR=/var/lib/neurovision/workspace \
  uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000
```

For multiple worker processes use uvicorn's `--workers N` (each worker imports the same
`app` via the import string — note: in-memory state is per-process; durable cross-process
state is a separate, out-of-scope concern).

---

## Startup configuration (env vars, all `NV_*`, documented defaults)

| Variable | Default | Meaning |
|---|---|---|
| `NV_HOST` | `127.0.0.1` | bind host |
| `NV_PORT` | `8000` | bind port (1..65535) |
| `NV_ENV` | `production` | `development` or `production` |
| `NV_LOG_LEVEL` | `info` | uvicorn log level (`critical`…`trace`) |
| `NV_RELOAD` | off | dev auto-reload (forced off in production) |
| `NV_WORKSPACE_DIR` | (service default) | workspace dir for the application service |
| `NV_ANALYSIS_SECONDS` | (platform default) | bounded analysis window (seconds) |

Configuration is typed + validated (`ServerConfig`); invalid values fail fast at startup
with `StartupConfigError`. Nothing is hidden — every option is an `NV_*` env var above.

---

## Lifecycle

* **Startup** — the application lifespan runs `build_application` → constructs the real
  service → builds the real Track-3 app → validates health/readiness/security/operations and
  records `app.state.startup_report`. A failed validation raises (no silent partial start).
* **Shutdown** — on SIGTERM/SIGINT the lifespan releases in-memory references (idempotent,
  never raises).

## Scope (DBE-1)

This package **only** makes the existing API launchable. It does not modify datasets, models,
inference, persistence, security, operations, Track 1-4, Docker, or any business logic.
