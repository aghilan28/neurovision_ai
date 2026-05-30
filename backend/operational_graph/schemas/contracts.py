"""Entity contracts for the operational-graph domain (V3-P4)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    GRAPH_DOMAIN_VERSION, GRAPH_IDENTITY_VERSION, GRAPH_ONTOLOGY_VERSION, GRAPH_NODE_VERSION,
    GRAPH_EDGE_VERSION, GRAPH_PROJECTION_VERSION, GRAPH_REGISTRY_VERSION, GRAPH_AUDIT_VERSION,
    GRAPH_LINEAGE_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    version_rule: str
    audit_rule: str
    lineage_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "version_rule": self.version_rule, "audit_rule": self.audit_rule,
                "lineage_rule": self.lineage_rule}


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "GraphNode": EntityContract(
        "GraphNode", GRAPH_NODE_VERSION, ("node_id", "node_type", "source_id"),
        ("node_id matches /^gnode\\+[0-9a-f]{16}$/", "node_type in the ontology",
         "every node references a real source artifact (no graph-only truth)"),
        "chained hash(state, previous)", "node creation audited",
        "parents reach the represented source artifact node (back to the patient)"),
    "GraphEdge": EntityContract(
        "GraphEdge", GRAPH_EDGE_VERSION,
        ("edge_id", "edge_type", "source_node", "target_node"),
        ("edge_id matches /^gedge\\+[0-9a-f]{16}$/", "edge_type in the ontology",
         "the (source_type -> target_type) pairing is permitted by the ontology",
         "endpoints are registered nodes; edge is derived_from real artifacts"),
        "chained hash(state, previous)", "edge creation audited",
        "parents reach the endpoint nodes"),
    "GraphRelationship": EntityContract(
        "GraphRelationship", GRAPH_DOMAIN_VERSION, ("relationship_id", "name", "edge_ids"),
        ("a relationship summarizes existing edges; adds no new truth",),
        "immutable per version", "relationship generation audited", "groups existing edges"),
    "GraphProjection": EntityContract(
        "GraphProjection", GRAPH_PROJECTION_VERSION,
        ("projection_id", "projection_type", "scope"),
        ("projection_id matches /^gproj\\+[0-9a-f]{16}$/",
         "a projection is a derived view (subset of registered nodes/edges)"),
        "chained hash(state, previous)", "projection generation audited",
        "parents reach the included node/edge artifacts"),
    "GraphOntology": EntityContract(
        "GraphOntology", GRAPH_ONTOLOGY_VERSION, ("node_types", "edge_types"),
        ("closed node/edge type sets", "relationship rules constrain edge pairings",
         "extensible: new types may be added; existing pairings immutable per version"),
        "versioned", "n/a", "n/a"),
    "GraphIdentity": EntityContract(
        "GraphIdentity", GRAPH_IDENTITY_VERSION, ("id", "kind"),
        ("node id derives from (node_type, source_id) — same source => same node",
         "edge id derives from (edge_type, endpoints)"),
        "stable across re-derivation", "minting audited via artifact creation", "n/a"),
    "GraphRegistryRecord": EntityContract(
        "GraphRegistryRecord", GRAPH_REGISTRY_VERSION,
        ("artifact_id", "artifact_kind", "version", "lineage_id"),
        ("no graph artifact exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current artifact version", "registry changes audited",
        "lineage_id references the artifact lineage node"),
    "GraphAuditRecord": EntityContract(
        "GraphAuditRecord", GRAPH_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "GraphLineageRecord": EntityContract(
        "GraphLineageRecord", GRAPH_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach source/endpoint nodes"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing
