"""``frontend/offline_research_app/reports`` — static offline HTML report (V1-P8).

Renders the application view-model into a single, dependency-free, deterministic
HTML page (CSS-only tabs, inline SVG charts) the researcher can open in any browser
offline. Renders only registered-artifact data — never recomputes anything.
"""

from __future__ import annotations

from .html_report import render_app_html, render_from_run_dir, write_app_html

__all__ = ["render_app_html", "render_from_run_dir", "write_app_html"]
