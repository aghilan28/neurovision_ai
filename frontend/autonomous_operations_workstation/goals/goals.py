"""Goal workspace (V4-P8) — registry, lifecycle, governance, audit, lineage, reports."""

from __future__ import annotations

from ..components import entity_pages


def goal_pages(state) -> list:
    return entity_pages(state, block="goals", page_id="goals", title="Goals",
                        id_label="goal_id")
