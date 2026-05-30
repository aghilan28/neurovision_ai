"""``frontend/autonomous_operations_workstation`` — Autonomous Operations Workstation (V4-P8).

The first unified **human-oversight** environment: the operational command center over
every Version 4 subsystem — Goals (V4-P1), Policies & Constraints (V4-P2), Plans
(V4-P3), Tasks (V4-P4), Agents (V4-P5), Executions (V4-P6) — plus the V4-P7 Governance
Intelligence Layer, and unified Audit, Lineage, Reports, and a System Health landing
area, through one coherent environment.

**Humans remain in control, accountable, and capable of intervention.** The
workstation is *observation, investigation, authorization, intervention, and
escalation* — it is **not** execution logic, planning logic, agent logic, or
governance logic. Its **intervention controls** (suspend agent, pause/terminate
execution, escalate approval, request review) are *governed descriptions* of backend
actions: each declares the authorization it requires and the audit + lineage +
governance records the backend will generate. No hidden actions — every control is
explicit and fully attributed.

**It is a presentation layer, not a source of truth.** Everything it displays
originates from *registered artifacts* — registries, registered reports, immutable
audit logs, the lineage graph, recorded validation results, and the governance
intelligence — serialized into a snapshot by
``scripts.build_autonomous_operations_workstation_snapshot``. The workstation reads
that snapshot with stdlib ``json`` only and imports **no** domain module (NR-8, the
strictest boundary). The only state it tracks is deterministic navigation context.

Public entry points:

* ``WorkstationState`` — load a snapshot (dict or path).
* ``build_workstation_view`` — assemble the full :class:`WorkstationView`.
* ``validate_state`` — the six presentation-integrity consistency checks.
"""

from __future__ import annotations

from .version import (
    AOW_WORKSTATION_VERSION, AOW_VIEWMODEL_VERSION, AOW_CONTROL_VERSION, AOW_STATE_VERSION,
)
from .schemas import (
    Section, Visualization, InterventionControl, Page, NavArea, ValidationReport,
    WorkstationView,
)
from .state import WorkstationState, CONTEXT_KEYS, ENTITY_BLOCKS
from .navigation import build_areas, area_ids, PRIMARY_AREAS
from .controls import build_controls, controls_summary
from .validation import validate_state
from .application import build_workstation_view, build_from_snapshot, build_from_path

__all__ = [
    "AOW_WORKSTATION_VERSION", "AOW_VIEWMODEL_VERSION", "AOW_CONTROL_VERSION", "AOW_STATE_VERSION",
    "Section", "Visualization", "InterventionControl", "Page", "NavArea", "ValidationReport",
    "WorkstationView", "WorkstationState", "CONTEXT_KEYS", "ENTITY_BLOCKS",
    "build_areas", "area_ids", "PRIMARY_AREAS", "build_controls", "controls_summary",
    "validate_state", "build_workstation_view", "build_from_snapshot", "build_from_path",
]
