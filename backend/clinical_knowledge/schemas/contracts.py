"""Entity contracts for the clinical-knowledge domain."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    TERMINOLOGY_VERSION, CONCEPT_VERSION, TAXONOMY_VERSION, ONTOLOGY_VERSION,
    RELATIONSHIP_VERSION, KNOWLEDGE_REGISTRY_VERSION, KNOWLEDGE_AUDIT_VERSION,
    KNOWLEDGE_LINEAGE_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    audit_rule: str
    lineage_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "audit_rule": self.audit_rule, "lineage_rule": self.lineage_rule}


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "Term": EntityContract(
        "Term", TERMINOLOGY_VERSION, ("term_id", "term", "definition", "source"),
        ("term_id matches /^term\\+[0-9a-f]{16}$/", "definition non-empty", "source recorded"),
        "term changes audited", "term node parents the knowledge source node"),
    "Concept": EntityContract(
        "Concept", CONCEPT_VERSION, ("concept_id", "name", "description"),
        ("concept_id matches /^concept\\+[0-9a-f]{16}$/", "relates to >= 1 term", "no diagnostic logic"),
        "concept changes audited", "concept node parents source + related-term nodes"),
    "TaxonomyNode": EntityContract(
        "TaxonomyNode", TAXONOMY_VERSION, ("taxon_id", "name", "category"),
        ("category in the allowed set", "parent exists", "hierarchy acyclic + depth-consistent"),
        "taxonomy changes audited", "taxon node parents its parent taxon node"),
    "RelationshipRecord": EntityContract(
        "RelationshipRecord", RELATIONSHIP_VERSION, ("relation_id", "subject_id", "predicate", "object_id"),
        ("predicate is known", "endpoint kinds match the predicate schema", "versioned"),
        "relationship changes audited", "relation node parents both endpoints"),
    "Ontology": EntityContract(
        "Ontology", ONTOLOGY_VERSION, ("entities", "relationships"),
        ("constraints hold", "practical (no reasoner)"), "ontology changes audited", "n/a"),
    "KnowledgeRegistryRecord": EntityContract(
        "KnowledgeRegistryRecord", KNOWLEDGE_REGISTRY_VERSION, ("version", "lineage_id"),
        ("versioned snapshots", "silent overwrite forbidden"),
        "registry changes audited", "lineage_id references the knowledge head node"),
    "KnowledgeAuditRecord": EntityContract(
        "KnowledgeAuditRecord", KNOWLEDGE_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "immutable; append-only; tamper-evident", "n/a"),
    "KnowledgeLineageRecord": EntityContract(
        "KnowledgeLineageRecord", KNOWLEDGE_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "lineage changes audited", "parents reach source/term/concept/taxon/relation nodes"),
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
