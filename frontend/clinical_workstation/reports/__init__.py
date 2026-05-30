"""Static-HTML rendering for the Clinical Workstation."""

from __future__ import annotations

from .html_report import (
    render_workstation_html, render_from_snapshot_path, write_workstation_html,
)

__all__ = ["render_workstation_html", "render_from_snapshot_path", "write_workstation_html"]
