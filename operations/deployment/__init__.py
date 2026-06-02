"""``operations/deployment`` — containerization definitions + validators (P8-C).

Provides the container build/run definitions (Dockerfiles + a compose file) and a
**static validator** for them. The environment here is Podman/Buildah with no
``docker compose`` provider, so compose is validated structurally (not via a compose
CLI), while real ``docker build``/``docker run`` of the slim frontend image proves the
build + startup process (see ``scripts/verify_productization_p8``).

Validation enforces deterministic, secret-free, reproducible builds: a pinned (non-latest)
base image, code copied in, a healthcheck, an explicit start command, and no secret values
baked into the image.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from ..version import OPERATIONS_DEPLOYMENT_VERSION

_THIS = os.path.dirname(__file__)
DOCKER_DIR = os.path.join(_THIS, "docker")
COMPOSE_DIR = os.path.join(_THIS, "compose")
BACKEND_DOCKERFILE = os.path.join(DOCKER_DIR, "Dockerfile.backend")
FRONTEND_DOCKERFILE = os.path.join(DOCKER_DIR, "Dockerfile.frontend")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yml")

# env-var names that must never have a baked-in value in an image definition
_SECRET_TOKENS = ("SECRET", "PASSWORD", "TOKEN", "PRIVATE_KEY", "API_KEY")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _instructions(text: str):
    """Yield (instruction, argument) for each non-comment Dockerfile line."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        yield parts[0].upper(), (parts[1] if len(parts) > 1 else "")


def validate_dockerfile(path: str, *, name: str) -> "list[Check]":
    checks: list[Check] = []
    if not os.path.exists(path):
        return [Check(f"{name}:exists", False, f"{path} missing")]
    text = open(path, "r", encoding="utf-8").read()
    instrs = list(_instructions(text))
    kinds = [i for i, _ in instrs]

    froms = [a for i, a in instrs if i == "FROM"]
    base_pinned = bool(froms) and all(":" in f and not f.strip().endswith(":latest") for f in froms)
    checks.append(Check(f"{name}:base_pinned", base_pinned,
                        f"FROM={froms}" if froms else "no FROM"))
    checks.append(Check(f"{name}:copies_code", "COPY" in kinds or "ADD" in kinds, "code copied in"))
    checks.append(Check(f"{name}:has_start_command", "CMD" in kinds or "ENTRYPOINT" in kinds,
                        "CMD/ENTRYPOINT present"))
    checks.append(Check(f"{name}:has_healthcheck", "HEALTHCHECK" in kinds, "HEALTHCHECK present"))
    checks.append(Check(f"{name}:has_workdir", "WORKDIR" in kinds, "WORKDIR present"))

    # no baked secrets: ENV/ARG NAME=VALUE where NAME looks secret and VALUE is non-empty
    leaks = []
    for instr, arg in instrs:
        if instr in ("ENV", "ARG") and "=" in arg:
            key, _, val = arg.partition("=")
            if any(tok in key.upper() for tok in _SECRET_TOKENS) and val.strip():
                leaks.append(key.strip())
    checks.append(Check(f"{name}:no_baked_secrets", not leaks, f"secret-like baked vars: {leaks}"))
    return checks


def validate_compose(path: str = COMPOSE_FILE) -> "list[Check]":
    """Structural validation of the compose file (no compose CLI available)."""
    checks: list[Check] = []
    if not os.path.exists(path):
        return [Check("compose:exists", False, f"{path} missing")]
    text = open(path, "r", encoding="utf-8").read()
    has = lambda token: token in text  # noqa: E731
    checks.append(Check("compose:has_services", re.search(r"^services:", text, re.M) is not None,
                        "services: block"))
    checks.append(Check("compose:backend_service", re.search(r"^\s{2}backend:", text, re.M) is not None,
                        "backend service"))
    checks.append(Check("compose:frontend_service",
                        re.search(r"^\s{2}frontend:", text, re.M) is not None, "frontend service"))
    checks.append(Check("compose:build_or_image", has("build:") or has("image:"),
                        "build/image defined"))
    checks.append(Check("compose:healthcheck", has("healthcheck:"), "healthcheck defined"))
    checks.append(Check("compose:shared_config", has("env_file") or has("environment:"),
                        "shared configuration"))
    checks.append(Check("compose:volumes", has("volumes:"), "persistent volume(s)"))
    # no inline secret values
    leak = re.search(r"(SECRET|PASSWORD|TOKEN)\w*\s*[:=]\s*(?!__INJECT|\$\{|\"\")\S+", text)
    checks.append(Check("compose:no_inline_secrets", leak is None,
                        "no inline secret values"))
    return checks


@dataclass(frozen=True)
class BuildPlan:
    name: str
    dockerfile: str
    context: str
    image_tag: str
    slim: bool

    def to_dict(self) -> dict:
        return {"name": self.name, "dockerfile": self.dockerfile, "context": self.context,
                "image_tag": self.image_tag, "slim": self.slim}


def build_plans(repo_root: str) -> "list[BuildPlan]":
    return [
        BuildPlan("frontend", FRONTEND_DOCKERFILE, repo_root, "neurovision-frontend:local", slim=True),
        BuildPlan("backend", BACKEND_DOCKERFILE, repo_root, "neurovision-backend:local", slim=False),
    ]


def validate_all() -> dict:
    checks = (validate_dockerfile(BACKEND_DOCKERFILE, name="backend")
              + validate_dockerfile(FRONTEND_DOCKERFILE, name="frontend")
              + validate_compose())
    return {
        "deployment_version": OPERATIONS_DEPLOYMENT_VERSION,
        "ok": all(c.passed for c in checks),
        "checks": [c.to_dict() for c in checks],
    }


def build_deployment_report() -> dict:
    return {"report_type": "deployment", **validate_all()}


__all__ = [
    "validate_dockerfile", "validate_compose", "validate_all", "build_deployment_report",
    "BuildPlan", "build_plans", "Check",
    "BACKEND_DOCKERFILE", "FRONTEND_DOCKERFILE", "COMPOSE_FILE",
]
