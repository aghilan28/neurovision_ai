"""Graph report builders (reproducible; version-tagged) (V3-P4)."""

from __future__ import annotations

from typing import Any

from ..version import GRAPH_REPORT_VERSION, OPERATIONAL_GRAPH_VERSION
from .. import ontology as ontology_mod


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "graph_report_version": GRAPH_REPORT_VERSION,
            "operational_graph_version": OPERATIONAL_GRAPH_VERSION, "scope": scope}


def build_graph_summary_report(registry: Any) -> dict:
    nodes_by_type: dict = {}
    for nid in registry.list_nodes():
        nt = registry.node(nid).node_type
        nodes_by_type[nt] = nodes_by_type.get(nt, 0) + 1
    edges_by_type: dict = {}
    for eid in registry.list_edges():
        et = registry.edge(eid).edge_type
        edges_by_type[et] = edges_by_type.get(et, 0) + 1
    return {**_header("graph_summary", "operational_graph"),
            "n_nodes": len(registry.list_nodes()), "n_edges": len(registry.list_edges()),
            "n_projections": len(registry.list_projections()),
            "nodes_by_type": dict(sorted(nodes_by_type.items())),
            "edges_by_type": dict(sorted(edges_by_type.items()))}


def build_node_report(registry: Any) -> dict:
    return {**_header("node", "operational_graph"),
            "nodes": [registry.node(nid).to_dict() for nid in registry.list_nodes()]}


def build_edge_report(registry: Any) -> dict:
    return {**_header("edge", "operational_graph"),
            "edges": [registry.edge(eid).to_dict() for eid in registry.list_edges()]}


def build_relationship_report(registry: Any) -> dict:
    return {**_header("relationship", "operational_graph"),
            "ontology": ontology_mod.to_dict(),
            "relationships": [registry.relationship(rid).to_dict()
                              for rid in registry.list_relationships()]}


def build_projection_report(registry: Any) -> dict:
    return {**_header("projection", "operational_graph"),
            "projections": [registry.projection(pid).to_dict()
                            for pid in registry.list_projections()]}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("graph_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("graph_audit", "operational_graph"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}
