"""Static file mount for the NeuroVision front-end.

The application STARTS on the landing page (``code.html`` — the Neurological
Intelligence Platform with the WebGL neural-graph shader). Authentication and
the upload sequence are reached explicitly:

- ``GET /``          -> ``code.html``     (LANDING PAGE — served first)
- ``GET /login``     -> ``auth.html``     (authentication portal)
- ``GET /auth``      -> ``auth.html``     (authentication portal alias)
- ``GET /upload``    -> ``upload.html``   (EEG upload & analysis sequence layer)
- ``GET /dashboard`` -> ``dashboard.html`` (authenticated Command Center)
- ``GET /patients``  -> placeholder.html  (patient records workspace)
- ``GET /export``    -> placeholder.html  (export center workspace)
- ``GET /status``    -> placeholder.html  (system status workspace)
- ``GET /telemetry`` -> production_output.json (engine telemetry)
- ``GET /static/...``-> files from the ``static/`` directory

Imported by the application factory to attach the static routes.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Resolve the project root robustly: the HTML entry points live at the repository
# root, while this module lives under ``backend/application_platform/server/``.
# Walk upward until each target page is found so resolution is correct regardless
# of the exact install layout (a fixed ``.parent.parent.parent`` off-by-one
# previously pointed at ``backend/`` and missed the pages entirely).
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent.parent


def _find_upwards(filename: str) -> Path:
    """Return the first ``filename`` found by walking up from this directory."""
    for candidate in _THIS_DIR.parents:
        target = candidate / filename
        if target.is_file():
            return target
    return _PROJECT_ROOT / filename


_LANDING_PAGE = _find_upwards("code.html")       # LANDING PAGE (served at /)
_AUTH_PAGE = _find_upwards("auth.html")           # authentication portal
_UPLOAD_PAGE = _find_upwards("upload.html")       # upload & analysis sequence
_DASHBOARD_PAGE = _find_upwards("dashboard.html") # authenticated Command Center
_PLACEHOLDER_PAGE = _find_upwards("placeholder.html") # workspace placeholders
_TELEMETRY_FILE = _find_upwards("production_output.json") # engine telemetry
_STATIC_DIR = _PROJECT_ROOT / "static"

_NO_CACHE = {"Cache-Control": "no-cache"}


def _serve(path: Path):
    """Build a no-cache ``FileResponse`` handler for ``path`` (404 if missing)."""
    async def _handler():
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"{path.name} not found")
        return FileResponse(path=str(path), media_type="text/html", headers=_NO_CACHE)
    return _handler


def _serve_telemetry(path: Path):
    """Serve the engine telemetry JSON (production_output.json) if present."""
    async def _handler():
        if not path.is_file():
            return JSONResponse({
                "status": "no_data",
                "metadata": {},
                "calibration_profile": {},
                "clinical_alerts_detected": [],
                "active_sessions": 0,
            }, headers=_NO_CACHE)
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"telemetry unreadable: {exc}")
        # Ensure the dashboard contract fields are present.
        if "active_sessions" not in data:
            data["active_sessions"] = 0
        return JSONResponse(data, headers=_NO_CACHE)
    return _handler


def mount_landing_page(app: FastAPI) -> None:
    """Attach the front-end page routes to the FastAPI application."""
    # Landing page is the application root -> the app STARTS here.
    app.add_api_route("/", _serve(_LANDING_PAGE), methods=["GET"], include_in_schema=False)
    # Authentication portal (reachable from the landing page's "Sign In").
    app.add_api_route("/login", _serve(_AUTH_PAGE), methods=["GET"], include_in_schema=False)
    app.add_api_route("/auth", _serve(_AUTH_PAGE), methods=["GET"], include_in_schema=False)
    # EEG upload & analysis sequence (the landing page modal routes here).
    app.add_api_route("/upload", _serve(_UPLOAD_PAGE), methods=["GET"], include_in_schema=False)
    # Authenticated Command Center (post-login destination).
    app.add_api_route("/dashboard", _serve(_DASHBOARD_PAGE), methods=["GET"], include_in_schema=False)
    # Future workspace placeholders (phase 1: routes are wired so navigation never 404s).
    app.add_api_route("/patients", _serve(_PLACEHOLDER_PAGE), methods=["GET"], include_in_schema=False)
    app.add_api_route("/export", _serve(_PLACEHOLDER_PAGE), methods=["GET"], include_in_schema=False)
    app.add_api_route("/status", _serve(_PLACEHOLDER_PAGE), methods=["GET"], include_in_schema=False)
    # Engine telemetry endpoint consumed by the dashboard.
    app.add_api_route("/telemetry", _serve_telemetry(_TELEMETRY_FILE), methods=["GET"], include_in_schema=False)

    # Mount the static directory if it exists.
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
