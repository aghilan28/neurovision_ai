"""``backend/application_platform/server/app.py`` — the authoritative ASGI entrypoint (DBE1-B/E).

This is the **single** production ASGI module. It exposes a module-level ``app`` (the real
Track-3 FastAPI application, built via the real ``ApplicationPlatformService``), so an
independent operator can start NeuroVision as a running HTTP service with either:

    uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000

or

    python -m backend.application_platform.server.app

Both launch the **same** application object through the **same** factory — there is no
duplicated initialization and no alternative bootstrap. The module-level ``app`` is created
lazily-but-once at import (the standard ASGI convention `uvicorn module:app` requires).

It changes no business logic; it only constructs (via the factory) and serves the existing
Track-3 API.
"""

from __future__ import annotations

import sys

from .config import load_config
from .factory import build_application

# The authoritative ASGI application + the service behind it. Imported once per process.
# `uvicorn backend.application_platform.server.app:app` binds to this `app`.
service, app = build_application(load_config())


def run() -> int:
    """Run the server with uvicorn using the validated startup configuration.

    Used by ``python -m backend.application_platform.server.app``. Serves the *same* ``app``
    object that ``uvicorn module:app`` serves (no duplicated init).
    """
    import uvicorn

    config = app.state.config
    # In reload mode uvicorn needs an import string (it re-imports in a child process); the
    # import string resolves to this very module's `app`, so it is the same application.
    target = "backend.application_platform.server.app:app" if config.reload else app
    uvicorn.run(
        target,
        host=config.host,
        port=config.port,
        log_level=config.log_level.value,
        reload=config.reload,
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
