"""``backend/application_platform/server/config.py`` — startup configuration (DBE1-D).

A single, typed, validated, deterministic source of server-startup configuration. All values
are read from ``NV_*`` environment variables with documented defaults — **no hidden
configuration**. Nothing here touches datasets / models / inference / security / persistence /
operations; it only parameterizes how the existing Track-3 FastAPI app is *served*.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ServerEnvironment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


_TRUE = {"1", "true", "yes", "on"}


class StartupConfigError(ValueError):
    """Raised when the startup configuration is invalid."""


@dataclass(frozen=True)
class ServerConfig:
    """Validated server-startup configuration (host / port / environment / log level / mode).

    Environment variables (all optional; documented defaults):

    * ``NV_HOST``            — bind host (default ``127.0.0.1``).
    * ``NV_PORT``            — bind port (default ``8000``; 1..65535).
    * ``NV_ENV``             — ``development`` | ``production`` (default ``production``).
    * ``NV_LOG_LEVEL``       — uvicorn log level (default ``info``).
    * ``NV_RELOAD``          — auto-reload (dev only; default off; forced off in production).
    * ``NV_WORKSPACE_DIR``   — workspace dir passed to the application service (optional).
    * ``NV_ANALYSIS_SECONDS``— bounded analysis window in seconds (default platform default).
    * ``NV_PROVISION_MODEL`` — provision a model on startup (default ``on``; set ``0``/``false``
      to disable, e.g. when an external model context is injected before serving).
    """

    host: str = "127.0.0.1"
    port: int = 8000
    environment: ServerEnvironment = ServerEnvironment.PRODUCTION
    log_level: LogLevel = LogLevel.INFO
    reload: bool = False
    workspace_dir: Optional[str] = None
    analysis_seconds: Optional[float] = None
    # MP-1: provision a model on startup so a fresh deploy reaches ready=true and uploads work.
    # On by default (the whole point of MP-1); operators can disable via NV_PROVISION_MODEL=0.
    provision_model: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host:
            raise StartupConfigError("host must be a non-empty string")
        if not (1 <= int(self.port) <= 65535):
            raise StartupConfigError(f"port must be in 1..65535, got {self.port}")
        if self.analysis_seconds is not None and self.analysis_seconds <= 0:
            raise StartupConfigError("analysis_seconds must be positive when set")

    @property
    def is_production(self) -> bool:
        return self.environment == ServerEnvironment.PRODUCTION

    def to_dict(self) -> dict:
        return {"host": self.host, "port": self.port, "environment": self.environment.value,
                "log_level": self.log_level.value, "reload": self.reload,
                "workspace_dir": self.workspace_dir, "analysis_seconds": self.analysis_seconds,
                "provision_model": self.provision_model}


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(name)
    return val if (val is not None and val != "") else default


def load_config(overrides: Optional[dict] = None) -> ServerConfig:
    """Build a :class:`ServerConfig` from ``NV_*`` env vars + optional explicit overrides.

    Overrides (a plain dict) take precedence over the environment — used by tests + the CLI.
    Deterministic: the same environment + overrides always yield the same config.
    """
    overrides = dict(overrides or {})

    def pick(key, env_name, transform=lambda x: x):
        if key in overrides and overrides[key] is not None:
            return overrides[key]
        raw = _env(env_name)
        return transform(raw) if raw is not None else None

    host = pick("host", "NV_HOST") or "127.0.0.1"
    port_val = pick("port", "NV_PORT", int)
    port = int(port_val) if port_val is not None else 8000

    env_raw = pick("environment", "NV_ENV")
    if isinstance(env_raw, ServerEnvironment):
        environment = env_raw
    elif env_raw is not None:
        try:
            environment = ServerEnvironment(str(env_raw).lower())
        except ValueError as exc:
            raise StartupConfigError(
                f"NV_ENV must be one of {[e.value for e in ServerEnvironment]}, got {env_raw!r}"
            ) from exc
    else:
        environment = ServerEnvironment.PRODUCTION

    level_raw = pick("log_level", "NV_LOG_LEVEL")
    if isinstance(level_raw, LogLevel):
        log_level = level_raw
    elif level_raw is not None:
        try:
            log_level = LogLevel(str(level_raw).lower())
        except ValueError as exc:
            raise StartupConfigError(
                f"NV_LOG_LEVEL must be one of {[lvl.value for lvl in LogLevel]}, got {level_raw!r}"
            ) from exc
    else:
        log_level = LogLevel.INFO

    if "reload" in overrides and overrides["reload"] is not None:
        reload = bool(overrides["reload"])
    else:
        reload = (_env("NV_RELOAD", "") or "").lower() in _TRUE

    workspace_dir = pick("workspace_dir", "NV_WORKSPACE_DIR")
    analysis_raw = pick("analysis_seconds", "NV_ANALYSIS_SECONDS", float)
    analysis_seconds = float(analysis_raw) if analysis_raw is not None else None

    if "provision_model" in overrides and overrides["provision_model"] is not None:
        provision_model = bool(overrides["provision_model"])
    else:
        raw = _env("NV_PROVISION_MODEL")
        # default ON; only an explicit falsey value disables provisioning.
        provision_model = True if raw is None else (raw.lower() in _TRUE)

    # Production never auto-reloads (a single authoritative, stable process).
    if environment == ServerEnvironment.PRODUCTION:
        reload = False

    return ServerConfig(host=host, port=port, environment=environment, log_level=log_level,
                        reload=reload, workspace_dir=workspace_dir,
                        analysis_seconds=analysis_seconds, provision_model=provision_model)


__all__ = ["ServerEnvironment", "LogLevel", "ServerConfig", "StartupConfigError", "load_config"]
