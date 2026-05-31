# NeuroVision AI — Deployment Guide (DBE-2)

This guide is for an **independent operator**. Following it yields a **running NeuroVision
HTTP API** — no source-code changes required. The container serves the real DBE-1 ASGI
entrypoint (`backend.application_platform.server.app:app`) via uvicorn and stays alive.

Deployment assets live in [`operations/deployment/`](../operations/deployment):
- `docker/Dockerfile.backend` — the API image (uvicorn serving the ASGI app).
- `docker/healthcheck.py` — stdlib HTTP healthcheck (probes `/health`).
- `compose/docker-compose.yml` — backend (API) + frontend services.

---

## Compose Startup Guide (recommended)

```bash
# from the repository root
docker compose -f operations/deployment/compose/docker-compose.yml up --build
```

This builds the image, starts the API on port **8000**, and keeps it running
(`restart: unless-stopped`). The compose `healthcheck` probes `/health` over real HTTP.

Validate (in another shell):

```bash
curl http://127.0.0.1:8000/health          # {"status":"ok",...}
curl http://127.0.0.1:8000/livez           # {"status":"alive",...}
curl http://127.0.0.1:8000/readyz          # {"status":"ready","ready":true,...}
curl http://127.0.0.1:8000/v1/readiness    # application readiness
curl http://127.0.0.1:8000/openapi.json    # full API contract
```

Stop (graceful SIGTERM → application lifespan shutdown):

```bash
docker compose -f operations/deployment/compose/docker-compose.yml down
```

---

## Docker Startup Guide (single container)

```bash
docker build -f operations/deployment/docker/Dockerfile.backend -t neurovision-backend .
docker run --rm -p 8000:8000 neurovision-backend
curl http://127.0.0.1:8000/health
docker stop <container>          # graceful shutdown
```

The image `EXPOSE`s 8000, runs as a non-root user, and its `HEALTHCHECK` calls
`operations/deployment/docker/healthcheck.py /health` (reports healthy only when the API is
actually serving HTTP).

---

## Operator Deployment Guide (exact, end to end)

```bash
git clone <repo> && cd neurovision_ai
docker compose -f operations/deployment/compose/docker-compose.yml up --build -d
# wait for healthy, then:
curl -fsS http://127.0.0.1:8000/health   && echo OK
curl -fsS http://127.0.0.1:8000/readyz   && echo READY
curl -fsS http://127.0.0.1:8000/openapi.json | head -c 80
docker compose -f operations/deployment/compose/docker-compose.yml down
```

No code edits are needed at any step.

---

## Deployment configuration (env vars; documented defaults)

The server reads `NV_*` env vars (typed + validated; see
`backend/application_platform/server/config.py`). The Dockerfile/compose set production
defaults:

| Variable | Compose/Image default | Meaning |
|---|---|---|
| `NV_HOST` | `0.0.0.0` | bind host (in-container) |
| `NV_PORT` | `8000` | bind port (published `8000:8000`) |
| `NV_ENV` | `production` | environment (forces reload off) |
| `NV_LOG_LEVEL` | `info` | uvicorn log level |
| `NV_WORKSPACE_DIR` | `/var/lib/neurovision/workspace` | service workspace (persistent volume) |

Secrets are never baked into the image; inject real values via the mounted `env_file`
(`operations/environments/*.env.template`).

---

## Container Validation Guide

```bash
# runtime-free verification of the deployment assets + the exact container start command:
python -m scripts.verify_dbe2_docker_deployment

# asset + container-start tests:
python -m pytest tests/test_docker_deployment.py
```

> Note: this sandbox has no container runtime (Podman/Buildah, no `docker compose`
> provider — see P8). The container *definitions* are validated structurally and the exact
> container start command (`uvicorn backend.application_platform.server.app:app`) is proven
> to serve live HTTP by launching it directly. On a host with Docker, the `docker`/`docker
> compose` commands above run the identical command inside the container.
