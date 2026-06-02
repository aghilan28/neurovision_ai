"""``backend/application_platform/server`` — runnable HTTP service entrypoint (DBE-1).

Turns the Track-3 FastAPI *application* into a runnable HTTP *service*: a single authoritative
ASGI entrypoint (``server.app:app``), a typed/validated startup configuration, an application
factory that constructs the real production service, and an application lifespan
(startup validation + graceful shutdown).

Public surface:

* ``ServerConfig`` / ``load_config`` — typed startup configuration (DBE1-D).
* ``build_service`` / ``build_application`` — the application factory (DBE1-C).
* ``StartupReport`` — the startup-validation record (DBE1-F).

The ASGI app itself lives at ``backend.application_platform.server.app:app`` (importing it
constructs the app once, per the ``uvicorn module:app`` convention). Importing *this* package
does NOT construct the app, so lightweight tooling can import the factory/config without
standing up the full service.
"""

from __future__ import annotations

from .config import (
    LogLevel, ServerConfig, ServerEnvironment, StartupConfigError, load_config,
)
from .factory import StartupReport, build_application, build_service

__all__ = [
    "LogLevel", "ServerConfig", "ServerEnvironment", "StartupConfigError", "load_config",
    "StartupReport", "build_application", "build_service",
]
