"""Final validation for DBE-1 — ASGI Entrypoint & Server Startup Fix.

Verifies the directive's 15 criteria against the **real** ASGI entrypoint: it imports the
authoritative ``backend.application_platform.server.app:app``, drives the application lifespan
(startup validation + graceful shutdown) via the FastAPI ``TestClient``, asserts the health /
readiness probes respond and security + operations initialize, and proves the server can be
launched for real with **uvicorn** (a bounded subprocess serving a live HTTP socket) and via
the **module** path — then stopped gracefully.

    python -m scripts.verify_dbe1_asgi_entrypoint
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[1]


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


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.application_platform.server import build_application, load_config

    # --- 1. ASGI app exists / 2. imports successfully ---
    app = None
    try:
        from backend.application_platform.server.app import app as imported_app
        from backend.application_platform.server.app import run as run_helper  # noqa: F401

        app = imported_app
        check("1. ASGI app exists", isinstance(app, FastAPI),
              "backend.application_platform.server.app:app")
        check("2. App imports successfully", app is not None and hasattr(app.state, "config"),
              "module-level app + state present")
    except Exception as exc:
        check("1. ASGI app exists", False, f"error: {exc}")
        check("2. App imports successfully", False, f"error: {exc}")

    # build a fresh app instance to drive the lifespan deterministically
    startup_report = None
    health_ok = readiness_ok = security_ok = operations_ok = startup_ok = shutdown_ok = False
    try:
        svc, app2 = build_application(load_config({}))
        with TestClient(app2) as c:
            startup_report = app2.state.startup_report
            startup_ok = bool(startup_report and startup_report.started)
            h = c.get("/health")
            health_ok = h.status_code == 200 and h.json()["status"] == "ok"
            rz = c.get("/readyz")
            readiness_ok = (c.get("/v1/readiness").status_code == 200
                            and rz.status_code == 200 and rz.json()["ready"] is True)
            # security: a real auth round-trip over the served API
            reg = c.post("/v1/auth/register", json={"username": "op", "password": "pw-123456"})
            log = c.post("/v1/auth/login", json={"username": "op", "password": "pw-123456"})
            security_ok = (reg.status_code == 201 and log.status_code == 200
                           and bool(startup_report and startup_report.security_ok))
            operations_ok = bool(startup_report and startup_report.operations_ok)
            svc._analyses["sentinel"] = object()
        # after the context exits, shutdown cleared the in-memory state
        shutdown_ok = svc._analyses == {}
    except Exception as exc:
        check("startup", False, f"error: {exc}")

    check("3. Startup succeeds", startup_ok and bool(startup_report and startup_report.ok),
          f"startup_report.ok={getattr(startup_report, 'ok', None)}")
    check("4. Shutdown succeeds", shutdown_ok, "lifespan shutdown cleared in-memory state")
    check("5. Health endpoint responds", health_ok, "/health -> 200 ok")
    check("6. Readiness endpoint responds", readiness_ok, "/readyz + /v1/readiness -> 200")
    check("7. Security initializes", security_ok, "register(201)+login(200); report.security_ok")
    check("8. Operations initialize", operations_ok, "OperationsPlatformService constructs")

    # --- 9. uvicorn startup works (real bounded subprocess) ---
    uvicorn_ok = False
    graceful = False
    port = 8763
    url = f"http://127.0.0.1:{port}"
    try:
        env = dict(os.environ, NV_HOST="127.0.0.1", NV_PORT=str(port), NV_ENV="production")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn",
             "backend.application_platform.server.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            if _wait_up(url, proc):
                with urllib.request.urlopen(url + "/health", timeout=3) as r:
                    uvicorn_ok = r.status == 200 and json.loads(r.read())["status"] == "ok"
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
                graceful = True
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        check("9. Uvicorn startup works", uvicorn_ok and graceful,
              f"uvicorn served live HTTP + graceful SIGTERM (rc={proc.returncode})")
    except Exception as exc:
        check("9. Uvicorn startup works", False, f"error: {exc}")

    # --- 10. module startup works (python -m ... ; bounded, then terminated) ---
    module_ok = False
    port2 = 8764
    url2 = f"http://127.0.0.1:{port2}"
    try:
        env = dict(os.environ, NV_HOST="127.0.0.1", NV_PORT=str(port2), NV_ENV="production")
        proc2 = subprocess.Popen(
            [sys.executable, "-m", "backend.application_platform.server.app"],
            cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            if _wait_up(url2, proc2):
                with urllib.request.urlopen(url2 + "/livez", timeout=3) as r:
                    module_ok = r.status == 200
        finally:
            proc2.send_signal(signal.SIGTERM)
            try:
                proc2.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc2.kill()
                proc2.wait(timeout=5)
        check("10. Module startup works", module_ok,
              "python -m backend.application_platform.server.app served live HTTP")
    except Exception as exc:
        check("10. Module startup works", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        proc3 = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                "tests/test_boundaries.py"], cwd=str(REPO),
                               capture_output=True, text=True)
        tail = proc3.stdout.strip().splitlines()[-1] if proc3.stdout.strip() else ""
        check("12. Repository boundaries preserved", proc3.returncode == 0, tail)
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- 13. determinism preserved (config) ---
    try:
        a = load_config({"host": "0.0.0.0", "port": 8080}).to_dict()
        b = load_config({"host": "0.0.0.0", "port": 8080}).to_dict()
        check("13. Determinism preserved", a == b, "same config inputs -> identical config")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. startup path documented ---
    try:
        doc = REPO / "backend" / "application_platform" / "server" / "README.md"
        txt = doc.read_text() if doc.exists() else ""
        documented = ("uvicorn backend.application_platform.server.app:app" in txt
                      and "python -m backend.application_platform.server.app" in txt)
        check("14. Startup path documented", documented, f"{doc.name} has exact start commands")
    except Exception as exc:
        check("14. Startup path documented", False, f"error: {exc}")

    # --- 11. tests pass ---
    try:
        proc4 = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                "tests/test_server_entrypoint.py"], cwd=str(REPO),
                               capture_output=True, text=True)
        tail = proc4.stdout.strip().splitlines()[-1] if proc4.stdout.strip() else ""
        check("11. Tests pass", proc4.returncode == 0, tail)
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 15. DBE-1 completed ---
    prior = {n: ok for n, ok, _ in checks}
    completed = all(ok for n, ok in prior.items() if not n.startswith("15."))
    check("15. DBE-1 completed", completed,
          "ASGI app + uvicorn path + module path + startup/shutdown verified")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDBE-1 — ASGI ENTRYPOINT & SERVER STARTUP — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("START COMMANDS:")
    print("  uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8000")
    print("  python -m backend.application_platform.server.app")
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
