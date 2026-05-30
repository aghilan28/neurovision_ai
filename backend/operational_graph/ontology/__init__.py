"""Operational graph ontology (V3-P4)."""

from __future__ import annotations

from .ontology import (
    NodeType, EdgeType, NODE_TYPES, EDGE_TYPES, RELATIONSHIP_RULES, OntologyError,
    is_node_type, is_edge_type, edge_allowed, validate_edge, to_dict,
)

__all__ = [
    "NodeType", "EdgeType", "NODE_TYPES", "EDGE_TYPES", "RELATIONSHIP_RULES", "OntologyError",
    "is_node_type", "is_edge_type", "edge_allowed", "validate_edge", "to_dict",
]
