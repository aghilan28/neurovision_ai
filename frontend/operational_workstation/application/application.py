"""Assemble the Operational Workstation view-model from a loaded snapshot.

This is the workstation's composition root: it seeds a deterministic navigation
context, builds every primary nav area, runs the workstation consistency
validation, and returns a single :class:`WorkstationView`. Everything it returns is
derived from registered artifacts in the snapshot (presentation only).
"""

from __future__ import annotations

from ..schemas import WorkstationView
from ..state import WorkstationState
from ..navigation import build_areas
from ..validation import validate_state
from ..version import OPERATIONAL_WORKSTATION_VERSION


def build_workstation_view(state: WorkstationState) -> WorkstationView:
    """Build the full, presentation-only operational workstation view-model."""
    state.default_context()
    areas = build_areas(state)
    validation = validate_state(state).to_dict()
    meta = {
        "workstation_version": OPERATIONAL_WORKSTATION_VERSION,
        "snapshot_version": state.snapshot.get("snapshot_version"),
        "n_events": len(state.event_records),
        "n_workflows": len(state.workflow_records),
        "n_analytics": len(state.analytics_blocks),
        "n_recommendations": len(state.recommendation_records),
        "context": state.context_snapshot(),
        "source": "registered artifacts only (presentation layer; no recomputation)",
    }
    return WorkstationView(areas=areas, validation=validation, meta=meta)


def build_from_snapshot(snapshot: dict) -> WorkstationView:
    return build_workstation_view(WorkstationState.from_snapshot(snapshot))


def build_from_path(snapshot_path: str) -> WorkstationView:
    return build_workstation_view(WorkstationState.load(snapshot_path))
