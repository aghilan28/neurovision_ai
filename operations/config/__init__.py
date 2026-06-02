"""``operations/config`` — configuration management (P8-D).

Loads configuration from environment variables (a ``NV_`` namespace) layered over
per-environment defaults, exposes a typed :class:`AppConfig`, resolves secrets through a
:class:`SecretsProvider` (env var or a mounted secrets file — **never** hardcoded), and
validates the result. No production secrets exist in the repository — only templates.

Determinism: given the same environment + overrides, the resolved config + its report are
identical. Secrets are always **redacted** in any serialized config or report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..util import fingerprint
from ..version import OPERATIONS_CONFIG_VERSION

ENVIRONMENTS = ("development", "testing", "staging", "production")
ENV_PREFIX = "NV_"
REDACTED = "***redacted***"
# Values that must never be accepted for a secret in a real (staging/production) env.
PLACEHOLDER_SECRETS = frozenset({"", "changeme", "change-me", "placeholder", "todo",
                                 "example", "secret", "default", REDACTED})


@dataclass(frozen=True)
class ConfigField:
    key: str                              # without the NV_ prefix
    default: Optional[str]
    kind: str = "str"                     # str | int | bool | path
    secret: bool = False
    required_in: tuple[str, ...] = ()     # environments where a real value is required
    description: str = ""

    @property
    def env_var(self) -> str:
        return f"{ENV_PREFIX}{self.key}"


# The configuration contract (the only configuration the platform reads).
CONFIG_SCHEMA: tuple[ConfigField, ...] = (
    ConfigField("ENV", "development", "str", required_in=ENVIRONMENTS,
                description="active runtime environment"),
    ConfigField("WORKSPACE_DIR", "./.nv_runtime", "path",
                description="root for content-addressed stores (raw/processed/uploads)"),
    ConfigField("BACKUP_DIR", "./.nv_backups", "path", description="backup destination root"),
    ConfigField("LOG_LEVEL", "info", "str", description="minimum structured-log level"),
    ConfigField("LOG_FORMAT", "json", "str", description="log encoding (json only)"),
    ConfigField("METRICS_ENABLED", "true", "bool", description="emit operational metrics"),
    ConfigField("PBKDF2_ITERATIONS", "200000", "int",
                description="auth KDF iterations (mirrors backend secure default)"),
    ConfigField("MODEL_ARCHITECTURE", "eegnet", "str", description="default model arch key"),
    ConfigField("AUTH_SECRET_KEY", None, "str", secret=True,
                required_in=("staging", "production"),
                description="server-side auth entropy seed (injected, never committed)"),
    ConfigField("ADMIN_BOOTSTRAP_PASSWORD", None, "str", secret=True,
                required_in=("staging", "production"),
                description="initial admin password (injected at deploy time only)"),
)
_BY_KEY = {f.key: f for f in CONFIG_SCHEMA}


class ConfigError(RuntimeError):
    """Raised on an invalid environment selection."""


class SecretsProvider:
    """Resolves secret values from the environment or a mounted secrets file.

    Never returns a hardcoded secret. A secrets file is ``KEY=VALUE`` lines (one per
    line); it is read at resolve time and is expected to be mounted/injected by the
    deployment environment, never committed.
    """

    def __init__(self, env: Optional[dict] = None, secrets_file: Optional[str] = None):
        self._env = dict(os.environ if env is None else env)
        self._file_values: dict[str, str] = {}
        path = secrets_file or self._env.get(f"{ENV_PREFIX}SECRETS_FILE")
        if path and os.path.exists(path):
            self._file_values = self._parse_secrets_file(path)

    @staticmethod
    def _parse_secrets_file(path: str) -> dict:
        out = {}
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def get(self, env_var: str) -> Optional[str]:
        if env_var in self._env and self._env[env_var] != "":
            return self._env[env_var]
        return self._file_values.get(env_var)


@dataclass(frozen=True)
class AppConfig:
    environment: str
    values: dict                          # resolved, typed values (secrets included)
    secret_keys: frozenset

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def to_dict(self, *, redact: bool = True) -> dict:
        out = {}
        for k, v in sorted(self.values.items()):
            out[k] = REDACTED if (redact and k in self.secret_keys) else v
        return {"config_version": OPERATIONS_CONFIG_VERSION, "environment": self.environment,
                "values": out, "secret_keys": sorted(self.secret_keys)}

    def signature(self) -> str:
        # secrets contribute only their presence, never their value (determinism + safety)
        safe = {k: (bool(self.values.get(k)) if k in self.secret_keys else self.values.get(k))
                for k in self.values}
        return fingerprint({"environment": self.environment, "values": safe})


def _coerce(field_: ConfigField, raw: Optional[str]):
    if raw is None:
        return None
    if field_.kind == "int":
        try:
            return int(raw)
        except ValueError:
            return raw            # left invalid; validator flags it
    if field_.kind == "bool":
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    return raw


class ConfigLoader:
    """Loads the typed application config for an environment from env + defaults."""

    def __init__(self, env: Optional[dict] = None, secrets: Optional[SecretsProvider] = None):
        self._env = dict(os.environ if env is None else env)
        self._secrets = secrets or SecretsProvider(env=self._env)

    def load(self, environment: Optional[str] = None, *, overrides: Optional[dict] = None) -> AppConfig:
        environment = environment or self._env.get(f"{ENV_PREFIX}ENV", "development")
        if environment not in ENVIRONMENTS:
            raise ConfigError(f"unknown environment {environment!r}; choose {ENVIRONMENTS}")
        overrides = overrides or {}
        values, secret_keys = {}, set()
        for f in CONFIG_SCHEMA:
            if f.key in overrides:
                raw = overrides[f.key]
            elif f.secret:
                raw = self._secrets.get(f.env_var)
            else:
                raw = self._env.get(f.env_var, f.default)
            values[f.key] = _coerce(f, raw if raw is not None else f.default)
            if f.secret:
                secret_keys.add(f.key)
        values["ENV"] = environment
        return AppConfig(environment=environment, values=values, secret_keys=frozenset(secret_keys))


@dataclass(frozen=True)
class ConfigCheck:
    name: str
    passed: bool
    detail: str = ""


class ConfigValidator:
    """Validates a resolved config: required keys present, types valid, and — in real
    environments — no placeholder/hardcoded secrets."""

    def validate(self, config: AppConfig) -> "list[ConfigCheck]":
        checks: list[ConfigCheck] = []
        env = config.environment
        for f in CONFIG_SCHEMA:
            val = config.values.get(f.key)
            if env in f.required_in:
                ok = val is not None and str(val) != ""
                checks.append(ConfigCheck(f"required:{f.key}", ok,
                                          "present" if ok else "missing required value"))
            if f.kind == "int":
                checks.append(ConfigCheck(f"type:{f.key}", isinstance(val, int) or val is None,
                                          f"int? got {type(val).__name__}"))
        # no placeholder secrets in staging/production
        if env in ("staging", "production"):
            for k in config.secret_keys:
                val = config.values.get(k)
                ok = val is not None and str(val).strip().lower() not in PLACEHOLDER_SECRETS
                checks.append(ConfigCheck(f"secret_strength:{k}", ok,
                                          "real secret present" if ok else "placeholder/empty secret"))
        # log format is machine-readable
        checks.append(ConfigCheck("log_format_json", config.values.get("LOG_FORMAT") == "json",
                                  f"log_format={config.values.get('LOG_FORMAT')}"))
        return checks


def build_config_report(config: AppConfig, checks: "list[ConfigCheck]") -> dict:
    return {
        "report_type": "config", "config_version": OPERATIONS_CONFIG_VERSION,
        "environment": config.environment, "config_signature": config.signature(),
        "ok": all(c.passed for c in checks),
        "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
        "config": config.to_dict(redact=True),
    }


__all__ = [
    "ENVIRONMENTS", "ENV_PREFIX", "REDACTED", "CONFIG_SCHEMA", "ConfigField", "ConfigError",
    "SecretsProvider", "AppConfig", "ConfigLoader", "ConfigValidator", "ConfigCheck",
    "build_config_report",
]
