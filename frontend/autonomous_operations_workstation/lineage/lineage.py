"""Lineage workspace (V4-P8) — the end-to-end traceability explorer.

Displays the deliverable spine

    Goal -> Policy -> Plan -> Task -> Agent -> Execution -> Governance Intelligence

and the full representative chain (Patient -> ... -> Governance Intelligence) the
backend recorded, as a traceability graph + ordered node table. Read-only.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, graph

# the deliverable lineage spine the workstation asserts is present end-to-end.
_SPINE = ["patient", "goal", "policy", "plan", "task", "agent", "execution",
          "governance_intelligence"]


def lineage_pages(state) -> list:
    rep = state.representative_chain
    records = rep.get("records", [])
    present_kinds = {r.get("kind") for r in records}

    node_rows = [[(r.get("lineage_id", "") or "")[:18], r.get("kind"),
                  len(r.get("parents", []))] for r in records]

    # build a small graph spec from the chain (node -> parent edges)
    ids = {r.get("lineage_id") for r in records}
    nodes = [{"id": (r.get("lineage_id", "") or "")[:18], "label": r.get("kind")}
             for r in records]
    edges = []
    for r in records:
        child = (r.get("lineage_id", "") or "")[:18]
        for p in r.get("parents", []):
            if p in ids:
                edges.append({"from": child, "to": (p or "")[:18]})

    sections = [
        kv_panel("Lineage Explorer", {
            "anchor": rep.get("anchor"), "verified": rep.get("verified", False),
            "n_nodes": len(records), "n_lineage_records": state.lineage.get("n_records", 0),
        }),
        badges("Deliverable Spine Present",
               [(kind, kind in present_kinds) for kind in _SPINE]),
        table("Chain (Patient -> ... -> Governance Intelligence)",
              ["lineage_id", "kind", "n_parents"], node_rows),
    ]
    viz = [graph("Traceability Graph", nodes, edges)]
    return [Page("lineage", "Lineage", sections, viz)]
