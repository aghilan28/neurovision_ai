"""serve_local.py — local runner for the NeuroVision platform on port 8080.

Serves the COMPLETE application through the real backend factory, so every route
is wired in one place:

    GET /          -> code.html      (the WebGL landing page — served FIRST)
    GET /login     -> auth.html      (authentication portal)
    GET /auth      -> auth.html      (authentication portal alias)
    GET /upload    -> upload.html    (EEG upload & analysis sequence)
    GET /dashboard -> dashboard.html (authenticated Command Center)
    GET /static/.. -> static assets
    GET /health    -> live platform telemetry
    /v1/..         -> the full product API (auth, uploads, analyses, reports, ...)

Run:
    python serve_local.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root (this file's directory) is importable as the top-level
# package root, so `backend.*` / `ml.*` resolve whether launched from any CWD.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

HOST = os.environ.get("NV_HOST", "0.0.0.0")
PORT = int(os.environ.get("NV_PORT", "8080"))


# ---------------------------------------------------------------------------
# PRIMARY: build the real app via the factory (full backend + all page routes).
# build_application() already calls mount_landing_page(app), which wires
# /, /login, /auth, /upload, /dashboard and /static.
# ---------------------------------------------------------------------------
def _build_full_app():
    from backend.application_platform.server.config import load_config
    from backend.application_platform.server.factory import build_application

    config = load_config({"host": HOST, "port": PORT})
    _service, app = build_application(config)
    # Belt-and-suspenders: guarantee the page routes are mounted even if a future
    # factory change drops the call.
    from backend.application_platform.server.landing import mount_landing_page
    mount_landing_page(app)
    return app


# ---------------------------------------------------------------------------
# FALLBACK: if the full backend cannot boot (e.g. a model/dependency issue),
# still serve every front-end page + a basic /health so navigation ALWAYS works.
# ---------------------------------------------------------------------------
def _build_fallback_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    root = _PROJECT_ROOT
    pages = {
        "/": "code.html",
        "/login": "auth.html",
        "/auth": "auth.html",
        "/upload": "upload.html",
        "/dashboard": "dashboard.html",
    }
    no_cache = {"Cache-Control": "no-cache"}

    app = FastAPI(title="NeuroVision (local)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
    )

    def serve(filename):
        async def _handler():
            path = root / filename
            if not path.is_file():
                raise HTTPException(status_code=404, detail=f"{filename} not found")
            return FileResponse(str(path), media_type="text/html", headers=no_cache)
        return _handler

    for route, filename in pages.items():
        app.add_api_route(route, serve(filename), methods=["GET"], include_in_schema=False)

    static_dir = root / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "neurovision-local", "version": "fallback",
                "model_prepared": False}

    return app


def main() -> int:
    print(f"\n  \u26a1 NeuroVision running at http://localhost:{PORT}\n")
    try:
        app = _build_full_app()
    except Exception as exc:  # noqa: BLE001
        print(f"  \u26a0\ufe0f  Full backend unavailable ({exc}).")
        print(f"     Running in page-serving mode: navigation works; /v1 API is offline.\n")
        app = _build_fallback_app()

    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
