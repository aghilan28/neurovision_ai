"""Plan workspace (V4-P8) — registry, dependencies, approvals, governance, audit, lineage."""

from __future__ import annotations

from ..components import entity_pages


def plan_pages(state) -> list:
    return entity_pages(state, block="plans", page_id="plans", title="Plans",
                        id_label="plan_id")
