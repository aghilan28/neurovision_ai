"""Assemble the Autonomous Operations Workstation view-model from a snapshot (V4-P8).

This is the workstation's composition root: it seeds a deterministic navigation
context, builds every primary nav area, gathers the governed intervention controls,
runs the workstation consistency validation, and returns a single
:class:`WorkstationView`. Everything it returns is derived from registered artifacts
in the snapshot (presentation + human-oversight surface only).
"""

from __future__ import annotations

from ..schemas import WorkstationView
from ..state import WorkstationState
from ..navigation import build_areas
from ..controls import build_controls, controls_summary
from ..validation import validate_state
from ..version import AOW_WORKSTATION_VERSION


def build_workstation_view(state: WorkstationState) -> WorkstationView:
    """Build the full, presentation-only autonomous-operations workstation view-model."""
    state.default_context()
    areas = build_areas(state)
    controls = build_controls(state)
    validation = validate_state(state).to_dict()
    intel = state.governance.get("intelligence", {})
    meta = {
        "workstation_version": AOW_WORKSTATION_VERSION,
        "snapshot_version": state.snapshot.get("snapshot_version"),
        "n_goals": len(state.records("goals")),
        "n_policies": len(state.records("policies")),
        "n_plans": len(state.records("plans")),
        "n_tasks": len(state.records("tasks")),
        "n_agents": len(state.records("agents")),
        "n_executions": len(state.records("executions")),
        "governance_health": intel.get("health_score"),
        "n_intervention_controls": len(controls),
        "controls_summary": controls_summary(controls),
        "context": state.context_snapshot(),
        "source": "registered artifacts only (presentation layer; no recomputation)",
    }
    return WorkstationView(areas=areas, validation=validation, meta=meta)


def build_from_snapshot(snapshot: dict) -> WorkstationView:
    return build_workstation_view(WorkstationState.from_snapshot(snapshot))


def build_from_path(snapshot_path: str) -> WorkstationView:
    return build_workstation_view(WorkstationState.load(snapshot_path))
