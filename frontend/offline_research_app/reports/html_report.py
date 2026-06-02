"""Design-system static HTML renderer for the offline research application."""

from __future__ import annotations

import os

from ...design_system import render_research_view
from ..pages import build_app_view
from ..schemas import AppView
from ..state import AppState
from ..version import OFFLINE_RESEARCH_APP_VERSION


def render_app_html(app_view: AppView) -> str:
    """Render the application view-model to deterministic research HTML."""
    return render_research_view(
        app_view,
        title="NeuroVision Research Environment",
        subtitle="Scientific intelligence workspace",
        version=OFFLINE_RESEARCH_APP_VERSION,
    )


def render_from_run_dir(run_dir: str) -> str:
    return render_app_html(build_app_view(AppState.load(run_dir)))


def write_app_html(run_dir: str, path: str | None = None) -> str:
    html_str = render_from_run_dir(run_dir)
    path = path or os.path.join(run_dir, "research_app.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return path
