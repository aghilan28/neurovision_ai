"""Container HTTP healthcheck (DBE-2).

A stdlib-only liveness/readiness probe for the containerized NeuroVision API. It performs a
real HTTP GET against the running service (the DBE-1 ASGI app served by uvicorn) and exits 0
iff the endpoint answers 200 — so a container orchestrator (Docker/Compose ``healthcheck:``)
reports the API as healthy only when it is actually serving HTTP, not merely when the process
exists.

Usage (inside the container):

    python operations/deployment/docker/healthcheck.py            # checks /health
    python operations/deployment/docker/healthcheck.py /readyz    # checks readiness

Host/port are read from ``NV_HOST`` / ``NV_PORT`` (the same env the server uses), defaulting
to ``127.0.0.1:8000``. Imports only the standard library — no heavy deps, no domain imports.
"""

from __future__ import annotations

import os
import sys
import urllib.request


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "/health"
    if not path.startswith("/"):
        path = "/" + path
    host = os.environ.get("NV_HEALTHCHECK_HOST", "127.0.0.1")
    port = os.environ.get("NV_PORT", "8000")
    url = f"http://{host}:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (loopback only)
            return 0 if 200 <= resp.status < 300 else 1
    except Exception as exc:  # noqa: BLE001 — any failure is an unhealthy container
        print(f"healthcheck failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
