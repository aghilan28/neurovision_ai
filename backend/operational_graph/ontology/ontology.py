"""Operational graph ontology (V3-P4).

A practical (not over-engineered) ontology: the closed sets of **node types** and
**edge types**, the relationship rules that say which edge types may connect which
node types, and the validation/extension rules. Every node/edge in the graph must
conform; the validator rejects anything else (ontology integrity).
"""

from __future__ import annotations

from ..version import GRAPH_ONTOLOGY_VERSION


class NodeType:
    PATIENT = "patient"
    CASE = "case"
    REVIEW = "review"
    FINDING = "finding"
    KNOWLEDGE = "knowledge"
    DECISION = "decision"
    EVENT = "event"
    TIMELINE = "timeline"
    WORKFLOW = "workflow"
    ANALYTICS = "analytics"


class EdgeType:
    OWNS = "owns"
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    INFLUENCES = "influences"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    RELATED_TO = "related_to"
    DERIVED_FROM = "derived_from"


NODE_TYPES: frozenset[str] = frozenset(v for k, v in vars(NodeType).items() if not k.startswith("_"))
EDGE_TYPES: frozenset[str] = frozenset(v for k, v in vars(EdgeType).items() if not k.startswith("_"))

# Relationship rules: edge_type -> tuple of (allowed_source_type, allowed_target_type).
# A pair (src, dst) is permitted if it appears for the edge type, or the edge type
# permits the wildcard "*" for that position. Practical, deterministic, extensible.
RELATIONSHIP_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    EdgeType.OWNS: ((NodeType.PATIENT, NodeType.CASE),),
    EdgeType.CONTAINS: ((NodeType.CASE, NodeType.REVIEW), (NodeType.REVIEW, NodeType.FINDING),
                        (NodeType.CASE, NodeType.FINDING)),
    EdgeType.PRODUCES: ((NodeType.REVIEW, NodeType.FINDING), (NodeType.FINDING, NodeType.DECISION),
                        (NodeType.WORKFLOW, NodeType.ANALYTICS)),
    EdgeType.CONSUMES: ((NodeType.DECISION, NodeType.FINDING), (NodeType.DECISION, NodeType.KNOWLEDGE)),
    EdgeType.INFLUENCES: ((NodeType.KNOWLEDGE, NodeType.FINDING), (NodeType.KNOWLEDGE, NodeType.DECISION)),
    EdgeType.DEPENDS_ON: (("*", "*"),),
    EdgeType.PRECEDES: ((NodeType.EVENT, NodeType.EVENT),),
    EdgeType.FOLLOWS: ((NodeType.EVENT, NodeType.EVENT),),
    EdgeType.DERIVED_FROM: (("*", "*"),),     # timelines/workflows/analytics derive from events/entities
    EdgeType.RELATED_TO: (("*", "*"),),
}


class OntologyError(ValueError):
    """Raised when a node/edge violates the ontology."""


def is_node_type(node_type: str) -> bool:
    return node_type in NODE_TYPES


def is_edge_type(edge_type: str) -> bool:
    return edge_type in EDGE_TYPES


def edge_allowed(edge_type: str, source_type: str, target_type: str) -> bool:
    if edge_type not in EDGE_TYPES:
        return False
    if source_type not in NODE_TYPES or target_type not in NODE_TYPES:
        return False
    rules = RELATIONSHIP_RULES.get(edge_type, ())
    for src, dst in rules:
        if (src in ("*", source_type)) and (dst in ("*", target_type)):
            return True
    return False


def validate_edge(edge_type: str, source_type: str, target_type: str) -> None:
    if not edge_allowed(edge_type, source_type, target_type):
        raise OntologyError(
            f"edge {edge_type!r} not permitted from {source_type!r} to {target_type!r}")


def to_dict() -> dict:
    return {
        "graph_ontology_version": GRAPH_ONTOLOGY_VERSION,
        "node_types": sorted(NODE_TYPES),
        "edge_types": sorted(EDGE_TYPES),
        "relationship_rules": {et: [list(p) for p in pairs]
                               for et, pairs in sorted(RELATIONSHIP_RULES.items())},
        "extension_rule": "new node/edge types may be added; existing pairs are immutable per version",
    }
