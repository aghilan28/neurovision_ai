"""Graph workspace — node/edge/relationship registry, projections, queries, reports."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import graph_structure


def graph_pages(state) -> list:
    block = state.graph
    registry = block.get("registry", {})
    projection = block.get("projection", {})
    audit = block.get("audit", {})

    # node counts by type
    node_types: dict = {}
    for n in registry.get("nodes", {}).values():
        nt = n.get("node_type", "?")
        node_types[nt] = node_types.get(nt, 0) + 1
    edge_types: dict = {}
    for e in registry.get("edges", {}).values():
        et = e.get("edge_type", "?")
        edge_types[et] = edge_types.get(et, 0) + 1

    proj_artifact = projection.get("artifact", {})

    sections = [
        kv_panel("Graph Registry", {
            "n_nodes": registry.get("n_nodes"), "n_edges": registry.get("n_edges"),
            "n_relationships": registry.get("n_relationships"),
            "n_projections": registry.get("n_projections"),
            "graph_registry_version": registry.get("graph_registry_version"),
            "audit_verified": audit.get("verified"),
        }),
        table("Node Registry (by type)", ["node_type", "count"], sorted(node_types.items())),
        table("Edge Registry (by type)", ["edge_type", "count"], sorted(edge_types.items())),
        kv_panel("Operational Projection", {
            "projection_id": (proj_artifact.get("projection_id") or "")[:18],
            "n_nodes": len(proj_artifact.get("node_ids", [])),
            "n_edges": len(proj_artifact.get("edge_ids", [])),
            "lineage_verified": projection.get("lineage_verified"),
        }),
        badges("Projection Validation",
               [(c["name"], c["passed"])
                for c in projection.get("validation", {}).get("checks", [])]),
    ]
    viz = [graph_structure(registry)]
    return [Page("graph", "Graph", sections, viz)]
