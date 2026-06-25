"""Static file mount for NeuroVision landing page.

Serves code.html at the root path and any static assets
from the /static URL prefix. This module is imported by
the application factory to attach the static route.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Resolve the project root (three levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LANDING_PAGE = _PROJECT_ROOT / "code.html"
_STATIC_DIR = _PROJECT_ROOT / "static"


def mount_landing_page(app: FastAPI) -> None:
    """Attach the landing page routes to the FastAPI application.

    - ``GET /``  → serves ``code.html`` (the NeuroVision SPA)
    - ``GET /static/...`` → serves files from the ``static/`` directory
    """
    @app.get("/", include_in_schema=False)
    async def serve_landing_page():
        """Serve the NeuroVision interactive landing page."""
        return FileResponse(
            path=str(_LANDING_PAGE),
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},
        )

    # Mount the static directory if it exists
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
