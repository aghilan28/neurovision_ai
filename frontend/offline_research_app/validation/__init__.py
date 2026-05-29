"""``frontend/offline_research_app/validation`` — application consistency checks (V1-P8).

Validates that what the app would display is internally consistent with the
registered artifacts: artifact consistency, registry consistency, output
consistency, version consistency, lineage consistency. Uses the frontend's own
``ValidationReport`` (no domain imports, NR-8).
"""

from __future__ import annotations

from .validators import AppValidator

__all__ = ["AppValidator"]
