"""Design-system static HTML renderer for the Operational Workstation."""

from __future__ import annotations

import os

from ...design_system import render_workstation_view
from ..application import build_workstation_view
from ..schemas import WorkstationView
from ..state import WorkstationState
from ..version import OPERATIONAL_WORKSTATION_VERSION


def render_workstation_html(view: WorkstationView) -> str:
    """Render the workstation view-model to deterministic operational HTML."""
    return render_workstation_view(
        view,
        title="NeuroVision Operational Intelligence Workstation",
        subtitle="Enterprise operations intelligence center",
        version=OPERATIONAL_WORKSTATION_VERSION,
    )


def render_from_snapshot_path(snapshot_path: str) -> str:
    return render_workstation_html(build_workstation_view(WorkstationState.load(snapshot_path)))


def write_workstation_html(snapshot_path: str, out_path: str | None = None) -> str:
    html_str = render_from_snapshot_path(snapshot_path)
    out_path = out_path or os.path.join(
        os.path.dirname(os.path.abspath(snapshot_path)), "operational_workstation.html"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return out_path
