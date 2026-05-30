"""Lineage workspace — explore the shared provenance graph end to end.

Presents the full mandated traceability ordering and the representative
Patient -> ... -> Recommendation chain that proves it.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import lineage_graph, traceability_graph

# The mandated end-to-end provenance ordering (lineage kinds, in order).
_CHAIN_ORDER = [
    ("Patient", "patient"), ("Case", "case"), ("Review", "review"),
    ("Finding", "finding"), ("Knowledge", "concept"), ("Decision", "interpretation"),
    ("Event", "event"), ("Timeline", "temporal_analytics"), ("Workflow", "workflow"),
    ("Graph", "graph_node"), ("Analytics", "analytics"), ("Recommendations", "recommendation"),
]


def lineage_pages(state) -> list:
    lineage = state.lineage
    records = lineage.get("records", {})
    rep = state.representative_chain

    # count nodes by kind (dependency profile)
    kind_counts: dict = {}
    for rec in records.values():
        kind_counts[rec.get("kind", "?")] = kind_counts.get(rec.get("kind", "?"), 0) + 1

    chain_present = {r.get("kind") for r in rep.get("records", [])}
    graph_present = set(kind_counts)
    present = chain_present | graph_present
    chain_rows = [[label, kind, kind in present] for label, kind in _CHAIN_ORDER]

    rep_rows = [[r.get("kind"), (r.get("lineage_id", "") or "").split("+")[-1][:8],
                 ", ".join(p.split("+")[-1][:6] for p in r.get("parents", []))]
                for r in rep.get("records", [])]

    sections = [
        kv_panel("Lineage Graph", {
            "n_records": lineage.get("n_records"),
            "lineage_version": lineage.get("lineage_version"),
            "representative_chain_verified": rep.get("verified"),
            "anchor": (rep.get("anchor") or "")[:24],
        }),
        badges("Traceability Chain (Patient → Recommendations)",
               [(label, kind in present) for label, kind in _CHAIN_ORDER]),
        table("Chain Coverage", ["stage", "lineage_kind", "present"], chain_rows),
        table("Dependency Profile (nodes by kind)", ["kind", "count"],
              sorted(kind_counts.items())),
        table("Representative Chain (nodes)", ["kind", "node", "parents"], rep_rows),
    ]
    viz = [traceability_graph(rep.get("records", [])), lineage_graph(lineage)]
    return [Page("lineage", "Lineage", sections, viz)]
