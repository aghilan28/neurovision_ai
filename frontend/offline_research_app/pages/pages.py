"""Assemble the application view-model from a loaded AppState."""

from __future__ import annotations

from ..schemas import AppView
from ..state import AppState
from ..workflows import all_workflows
from ..validation import AppValidator
from ..version import OFFLINE_RESEARCH_APP_VERSION


def build_app_view(state: AppState) -> AppView:
    """Build the full, presentation-only application view-model."""
    pages = all_workflows(state)
    validation = AppValidator().validate(state).to_dict()
    meta = {
        "app_version": OFFLINE_RESEARCH_APP_VERSION,
        "inference_id": state.index["inference_id"],
        "lineage_id": state.index["lineage_id"],
        "run_dir": state.run_dir,
        "source": "registered artifacts only (presentation layer; no recomputation)",
    }
    return AppView(pages=pages, validation=validation, meta=meta)
