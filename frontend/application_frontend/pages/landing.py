"""Landing page controller for NeuroVision frontend.

This module provides the server-side entry point for the NeuroVision
interactive landing page (code.html). It integrates with the FastAPI
static mount system to serve the production landing page at the root
URL path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


# Path to the landing page HTML file (project root / code.html)
_LANDING_PAGE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "code.html"


def get_landing_page_path() -> Optional[str]:
    """Return the filesystem path to code.html if it exists, else None."""
    if _LANDING_PAGE_PATH.is_file():
        return str(_LANDING_PAGE_PATH)
    return None


def landing_page_available() -> bool:
    """Check whether the landing page HTML file exists on disk."""
    return _LANDING_PAGE_PATH.is_file()
