"""``frontend/offline_research_app/state`` — application state (V1-P8).

Loads a backend run directory's **registered artifacts** (JSON) and tracks the
current dataset / model / benchmark / inference / reports / artifacts / audit
trail. Everything the app displays originates here — never recomputed.
"""

from __future__ import annotations

from .app_state import AppState

__all__ = ["AppState"]
