"""``operations/environments`` — runtime environment definitions (P8-B).

Declares the four runtime environments (development, testing, staging, production) and,
for each, its configuration profile, dependency set, storage layout, secrets *structure*
(names only — never values), and operational requirements. The accompanying
``*.env.template`` files document the environment variables to inject; they contain **no
real secrets**.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..config import ENVIRONMENTS
from ..version import OPERATIONS_ENVIRONMENT_VERSION

_TEMPLATE_DIR = os.path.dirname(__file__)
RUNTIME_DEPENDENCIES = ("numpy==2.4.6", "mne==1.12.1", "scipy==1.17.1")
DEV_DEPENDENCIES = ("pytest==9.0.3", "ruff==0.15.15")


@dataclass(frozen=True)
class EnvironmentSpec:
    name: str
    description: str
    debug: bool
    config_overrides: dict
    dependencies: tuple
    storage: dict                          # logical storage areas -> purpose
    secret_names: tuple                    # required secret env-var names (structure only)
    operational_requirements: tuple

    @property
    def template_file(self) -> str:
        return os.path.join(_TEMPLATE_DIR, f"{self.name}.env.template")

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description, "debug": self.debug,
            "config_overrides": self.config_overrides, "dependencies": list(self.dependencies),
            "storage": self.storage, "secret_names": list(self.secret_names),
            "operational_requirements": list(self.operational_requirements),
            "template_file": os.path.basename(self.template_file),
        }


_STORAGE = {
    "workspace": "content-addressed raw/processed/feature stores + uploads",
    "backups": "registry + config + artifact backups",
    "logs": "structured JSON log stream (stdout in containers)",
}

ENVIRONMENT_SPECS: dict = {
    "development": EnvironmentSpec(
        "development", "Local developer environment (synthetic fixtures, verbose logs).",
        debug=True,
        config_overrides={"LOG_LEVEL": "debug", "METRICS_ENABLED": "true"},
        dependencies=RUNTIME_DEPENDENCIES + DEV_DEPENDENCIES,
        storage=_STORAGE, secret_names=(),
        operational_requirements=("python>=3.11", "local filesystem", "no secrets required")),
    "testing": EnvironmentSpec(
        "testing", "Automated test/CI environment (deterministic, ephemeral storage).",
        debug=True,
        config_overrides={"LOG_LEVEL": "warning", "METRICS_ENABLED": "true"},
        dependencies=RUNTIME_DEPENDENCIES + DEV_DEPENDENCIES,
        storage=_STORAGE, secret_names=(),
        operational_requirements=("python>=3.11", "ephemeral tmp storage",
                                  "deterministic entropy for auth")),
    "staging": EnvironmentSpec(
        "staging", "Pre-production environment mirroring production (real secrets injected).",
        debug=False,
        config_overrides={"LOG_LEVEL": "info", "METRICS_ENABLED": "true"},
        dependencies=RUNTIME_DEPENDENCIES,
        storage=_STORAGE,
        secret_names=("NV_AUTH_SECRET_KEY", "NV_ADMIN_BOOTSTRAP_PASSWORD"),
        operational_requirements=("python>=3.11", "persistent volume for workspace+backups",
                                  "injected secrets (env or mounted file)",
                                  "health + readiness probes")),
    "production": EnvironmentSpec(
        "production", "Production environment (real secrets, persistent storage, probes).",
        debug=False,
        config_overrides={"LOG_LEVEL": "info", "METRICS_ENABLED": "true"},
        dependencies=RUNTIME_DEPENDENCIES,
        storage=_STORAGE,
        secret_names=("NV_AUTH_SECRET_KEY", "NV_ADMIN_BOOTSTRAP_PASSWORD"),
        operational_requirements=("python>=3.11", "persistent volume for workspace+backups",
                                  "injected secrets (never committed)", "health/readiness/liveness",
                                  "scheduled backups", "log + metrics collection")),
}


def get_environment(name: str) -> EnvironmentSpec:
    if name not in ENVIRONMENT_SPECS:
        raise KeyError(f"unknown environment {name!r}; choose {tuple(ENVIRONMENT_SPECS)}")
    return ENVIRONMENT_SPECS[name]


def all_environments() -> list:
    return [ENVIRONMENT_SPECS[n] for n in ENVIRONMENTS]


def build_environments_report() -> dict:
    return {
        "report_type": "environments", "environment_version": OPERATIONS_ENVIRONMENT_VERSION,
        "environments": {n: ENVIRONMENT_SPECS[n].to_dict() for n in ENVIRONMENTS},
    }


__all__ = [
    "EnvironmentSpec", "ENVIRONMENT_SPECS", "RUNTIME_DEPENDENCIES", "DEV_DEPENDENCIES",
    "get_environment", "all_environments", "build_environments_report",
]
