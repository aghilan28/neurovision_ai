"""Application frontend layout renderer.

This module delegates presentation to the shared NeuroVision design system while
preserving the existing page view-model contract.
"""

from __future__ import annotations

from ...design_system import render_application_page
from ..version import APPLICATION_FRONTEND_VERSION


def render(page: dict) -> str:
    """Render a Page dict into a complete, deterministic HTML document."""
    return render_application_page(page, version=APPLICATION_FRONTEND_VERSION)


__all__ = ["render"]
