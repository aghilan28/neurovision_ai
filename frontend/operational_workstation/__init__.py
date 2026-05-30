"""``frontend/operational_workstation`` — Operational Intelligence Workstation (V3-P7).

The first unified **operational** workflow application: the primary interface over
every Version 3 subsystem — Operational Events (V3-P1), Temporal Intelligence
(V3-P2), Workflow Intelligence (V3-P3), the Operational Graph (V3-P4), Operational
Analytics (V3-P5), and Operational Recommendations (V3-P6) — plus unified Audit,
Lineage, Reports, and a System Health landing area, through one coherent
environment.

**It is a presentation layer, not a source of truth.** Everything it displays
originates from *registered artifacts* — registries, registered reports, immutable
audit logs, the lineage graph, and recorded validation results — serialized into a
snapshot by ``scripts.build_operational_workstation_snapshot``. The workstation reads
that snapshot with stdlib ``json`` only and imports **no** domain module (NR-8, the
strictest boundary). It creates no hidden state; the only state it tracks is
deterministic navigation context. It is **not** a workflow/analytics/recommendation
engine — it exposes the operational system, it does not create operational logic.

Public entry points:

* ``WorkstationState`` — load a snapshot (dict or path).
* ``build_workstation_view`` — assemble the full :class:`WorkstationView`.
* ``render_workstation_html`` / ``write_workstation_html`` — deterministic static HTML.
* ``validate_state`` — the six presentation-integrity consistency checks.
"""

from __future__ import annotations

from .version import (
    OPERATIONAL_WORKSTATION_VERSION, OPERATIONAL_VIEWMODEL_VERSION,
    OPERATIONAL_VISUALIZATION_VERSION, OPERATIONAL_STATE_VERSION,
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
    "OPERATIONAL_WORKSTATION_VERSION", "OPERATIONAL_VIEWMODEL_VERSION",
    "OPERATIONAL_VISUALIZATION_VERSION", "OPERATIONAL_STATE_VERSION",
    "Section", "Visualization", "Page", "NavArea", "ValidationReport", "WorkstationView",
    "WorkstationState", "CONTEXT_KEYS",
    "build_areas", "area_ids", "PRIMARY_AREAS",
    "validate_state",
    "build_workstation_view", "build_from_snapshot", "build_from_path",
    "render_workstation_html", "render_from_snapshot_path", "write_workstation_html",
]
