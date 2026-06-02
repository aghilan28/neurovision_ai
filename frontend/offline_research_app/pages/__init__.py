"""``frontend/offline_research_app/pages`` — page assembly (V1-P8).

Assembles the five workflow pages + app-consistency validation into a single
``AppView`` view-model (and is the input to the static HTML report).
"""

from __future__ import annotations

from .pages import build_app_view

__all__ = ["build_app_view"]
