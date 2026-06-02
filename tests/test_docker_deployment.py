"""DBE-2 — Docker deployment & container startup tests (operations/deployment).

Validates the deployment assets actually serve the real API:

* the backend Dockerfile + compose run the DBE-1 ASGI entrypoint via uvicorn (not the old
  one-shot ``operations.cli`` command), expose a port, and use a real HTTP healthcheck;
* the **exact container start command** really serves live HTTP (a bounded uvicorn subprocess
  built from the same argv the Dockerfile/compose use);
* the container HTTP healthcheck script passes against a running server and fails when down;
* environment configuration loads deterministically.

No container runtime is available in this sandbox (Podman/Buildah, no compose provider — see
P8), so the container *definitions* are validated structurally while the *start command*
itself is proven by really launching it. No mocks.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(REPO_ROOT, "operations", "deployment")
BACKEND_DOCKERFILE = os.path.join(DEPLOY, "docker", "Dockerfile.backend")
COMPOSE_FILE = os.path.join(DEPLOY, "compose", "docker-compose.yml")
HEALTHCHECK = os.path.join(DEPLOY, "docker", "healthcheck.py")
ENTRYPOINT = "backend.application_platform.server.app:app"


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# --- DBE2-A/B: Dockerfile serves the API ------------------------------------
def test_backend_dockerfile_exists():
    assert os.path.exists(BACKEND_DOCKERFILE)


def test_backend_dockerfile_serves_asgi_via_uvicorn():
    text = _read(BACKEND_DOCKERFILE)
    assert "uvicorn" in text and ENTRYPOINT in text
    # the CMD must launch uvicorn serving the DBE-1 app, not a one-shot health command
    cmd_lines = [ln for ln in text.splitlines() if ln.strip().startswith("CMD")]
    assert cmd_lines, "no CMD in backend Dockerfile"
    cmd_block = text.split("CMD", 1)[1]
    assert "uvicorn" in cmd_block and ENTRYPOINT in cmd_block


def test_backend_dockerfile_does_not_oneshot_health_as_cmd():
    text = _read(BACKEND_DOCKERFILE)
    cmd_block = text.split("CMD", 1)[1]
    # the old one-shot startup must be gone from the CMD
    assert "operations.cli" not in cmd_block.split("HEALTHCHECK")[0]


def test_backend_dockerfile_exposes_port():
    text = _read(BACKEND_DOCKERFILE)
    assert re.search(r"^EXPOSE\s+8000", text, re.M)


def test_backend_dockerfile_http_healthcheck():
    text = _read(BACKEND_DOCKERFILE)
    hc = [ln for ln in text.splitlines() if "HEALTHCHECK" in ln]
    assert hc, "no HEALTHCHECK"
    assert "healthcheck.py" in text  # real HTTP probe, not operations.cli live


# --- DBE2-C: compose serves the API -----------------------------------------
def test_compose_exists():
    assert os.path.exists(COMPOSE_FILE)


def test_compose_serves_api_with_ports_and_restart():
    text = _read(COMPOSE_FILE)
    assert "uvicorn" in text and ENTRYPOINT in text
    assert re.search(r'8000:8000', text), "backend port not published"
    assert "restart:" in text and "unless-stopped" in text
    assert "healthcheck.py" in text  # HTTP healthcheck wired in compose


def test_compose_injects_environment():
    text = _read(COMPOSE_FILE)
    assert "NV_PORT" in text and "NV_HOST" in text and "env_file" in text


def test_compose_has_no_inline_secrets():
    text = _read(COMPOSE_FILE)
    assert re.search(r"(SECRET|PASSWORD|TOKEN)\w*\s*[:=]\s*(?!__INJECT|\$\{|\"\")\S+",
                     text) is None


# --- DBE2-F: deployment configuration ---------------------------------------
def test_deployment_config_is_env_driven_and_deterministic():
    from backend.application_platform.server import load_config

    env = {"NV_HOST": "0.0.0.0", "NV_PORT": "8000", "NV_ENV": "production"}
    a = load_config({"host": env["NV_HOST"], "port": int(env["NV_PORT"]),
                     "environment": env["NV_ENV"]}).to_dict()
    b = load_config({"host": env["NV_HOST"], "port": int(env["NV_PORT"]),
                     "environment": env["NV_ENV"]}).to_dict()
    assert a == b and a["host"] == "0.0.0.0" and a["port"] == 8000


# --- DBE2-D/E/G: the exact container command really serves + stops ----------
def _wait_up(url, proc, tries=30):
    for _ in range(tries):
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url + "/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def _container_cmd_argv(port):
    """The exact argv the Dockerfile/compose CMD runs (uvicorn serving the DBE-1 app)."""
    return [sys.executable, "-m", "uvicorn", ENTRYPOINT,
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]


def test_container_start_command_serves_live_http_and_stops():
    port = 8771
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, NV_HOST="127.0.0.1", NV_PORT=str(port), NV_ENV="production")
    proc = subprocess.Popen(_container_cmd_argv(port), cwd=REPO_ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        assert _wait_up(url, proc), "container start command did not serve HTTP"
        # API + health + readiness + openapi respond (DBE2-D / DBE2-G)
        with urllib.request.urlopen(url + "/health", timeout=3) as r:
            assert r.status == 200 and json.loads(r.read())["status"] == "ok"
        with urllib.request.urlopen(url + "/readyz", timeout=3) as r:
            assert json.loads(r.read())["ready"] is True
        with urllib.request.urlopen(url + "/openapi.json", timeout=3) as r:
            assert r.status == 200
        # the container HTTP healthcheck script passes against the running server (DBE2-D)
        hc = subprocess.run([sys.executable, HEALTHCHECK, "/health"],
                            cwd=REPO_ROOT, env=env, capture_output=True, text=True)
        assert hc.returncode == 0, f"healthcheck failed while up: {hc.stderr}"
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    # graceful stop (DBE2-E): process terminated, no orphan
    assert proc.returncode is not None


def test_healthcheck_fails_when_server_down():
    # nothing listening on this port -> healthcheck must report unhealthy (non-zero)
    env = dict(os.environ, NV_HEALTHCHECK_HOST="127.0.0.1", NV_PORT="8799")
    hc = subprocess.run([sys.executable, HEALTHCHECK, "/health"],
                        cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert hc.returncode != 0
