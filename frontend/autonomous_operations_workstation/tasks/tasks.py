"""Task workspace (V4-P8) — registry, dependencies, assignments, governance, audit, lineage."""

from __future__ import annotations

from ..components import entity_pages


def task_pages(state) -> list:
    return entity_pages(state, block="tasks", page_id="tasks", title="Tasks",
                        id_label="task_id")
