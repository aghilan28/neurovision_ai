"""Policy workspace (V4-P8) — registry, constraints, evaluations, governance, audit, lineage."""

from __future__ import annotations

from ..components import entity_pages, kv_panel, table


def policy_pages(state) -> list:
    pages = entity_pages(state, block="policies", page_id="policies", title="Policies",
                         id_label="policy_id")
    # add a constraints panel to the policy page
    constraints = state.constraints()
    page = pages[0]
    page.sections.append(kv_panel("Constraints", {"n_constraints": len(constraints)}))
    page.sections.append(table(
        "Constraints", ["constraint_id", "state", "lineage"],
        [[(c.get("id", "") or "")[:18], c.get("state", ""), c.get("lineage_verified", False)]
         for c in constraints]))
    return pages
