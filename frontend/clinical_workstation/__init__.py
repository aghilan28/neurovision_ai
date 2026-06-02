"""``frontend/clinical_workstation`` — Clinical Workstation (V2-P7).

The first unified workflow application: the primary operational interface over
every Version 2 subsystem (Patient → Case → Study → Review → Finding →
Interpretation → Knowledge → Multi-Case Intelligence → Decision Support), plus
unified Audit, Lineage, and Reporting workspaces.

**It is a presentation layer, not a source of truth.** Everything it displays
originates from *registered artifacts* — registries, registered reports, immutable
audit logs, the lineage graph, and recorded validation results — serialized into a
snapshot by ``scripts.build_workstation_snapshot``. The workstation reads that
snapshot with stdlib ``json`` only and imports **no** domain module (NR-8, the
strictest boundary: ``frontend`` imports nothing internal). It creates no hidden
state; the only state it tracks is deterministic navigation context.

Public entry points:

* ``WorkstationState`` — load a snapshot (dict or path).
* ``build_workstation_view`` — assemble the full :class:`WorkstationView`.
* ``render_workstation_html`` / ``write_workstation_html`` — deterministic static HTML.
* ``validate_state`` — the seven presentation-integrity consistency checks.
"""

from __future__ import annotations

from .version import (
    CLINICAL_WORKSTATION_VERSION, WORKSTATION_VIEWMODEL_VERSION,
    WORKSTATION_VISUALIZATION_VERSION, WORKSTATION_STATE_VERSION,
)
from .schemas import (
    Section, Visualization, Page, NavArea, ValidationReport, WorkstationView,
)
from .state import WorkstationState, CONTEXT_KEYS
from .navigation import build_areas, area_ids, PRIMARY_AREAS
from .validation import validate_state
from .application import build_workstation_view, build_from_snapshot, build_from_path
from .reports import render_workstation_html, render_from_snapshot_path, write_workstation_html

__all__ = [
    "CLINICAL_WORKSTATION_VERSION", "WORKSTATION_VIEWMODEL_VERSION",
    "WORKSTATION_VISUALIZATION_VERSION", "WORKSTATION_STATE_VERSION",
    "Section", "Visualization", "Page", "NavArea", "ValidationReport", "WorkstationView",
    "WorkstationState", "CONTEXT_KEYS",
    "build_areas", "area_ids", "PRIMARY_AREAS",
    "validate_state",
    "build_workstation_view", "build_from_snapshot", "build_from_path",
    "render_workstation_html", "render_from_snapshot_path", "write_workstation_html",
]
