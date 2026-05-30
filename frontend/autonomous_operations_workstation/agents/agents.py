"""Agent workspace (V4-P8) — registry, capabilities, assignments, governance, audit, lineage.

Surfaces the governed *suspend agent* intervention control for each agent.
"""

from __future__ import annotations

from ..components import entity_pages
from ..controls import controls_for_agent


def agent_pages(state) -> list:
    extra = [
        ("capabilities", lambda r: len(r.get("capabilities", []))),
        ("assignments", lambda r: len(r.get("assignments", []))),
    ]
    controls = []
    for agent in state.records("agents"):
        controls.extend(controls_for_agent(agent))
    return entity_pages(state, block="agents", page_id="agents", title="Agents",
                        id_label="agent_id", extra_columns=extra, controls=controls)
