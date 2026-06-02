"""Clinical knowledge domain entities (V2-P4).

Pure data + ``to_dict`` + ``signature``. Registries/managers live in their
subsystems; orchestration in ``service.py``. These shapes are descriptive
terminology/concepts/relationships — they encode no diagnostic or decision logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    TERMINOLOGY_VERSION, CONCEPT_VERSION, TAXONOMY_VERSION, RELATIONSHIP_VERSION,
    KNOWLEDGE_EVIDENCE_VERSION, KNOWLEDGE_REGISTRY_VERSION, KNOWLEDGE_AUDIT_VERSION,
    KNOWLEDGE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


@dataclass(frozen=True)
class Term:
    """A versioned terminology entry (e.g. IIC, LPD, GPD, seizure, calibration)."""

    term_id: str
    term: str
    definition: str
    source: str
    status: str = "active"          # active|deprecated
    related_terms: tuple[str, ...] = ()
    version: str = TERMINOLOGY_VERSION

    def signature(self) -> str:
        return hash_obj({"term_id": self.term_id, "term": self.term, "definition": self.definition,
                         "source": self.source, "status": self.status,
                         "related_terms": list(self.related_terms)})

    def to_dict(self) -> dict:
        return {"term_id": self.term_id, "term": self.term, "definition": self.definition,
                "source": self.source, "status": self.status,
                "related_terms": list(self.related_terms), "version": self.version,
                "signature": self.signature()}


@dataclass(frozen=True)
class Concept:
    """A versioned clinical/EEG concept, related to terms + evidence."""

    concept_id: str
    name: str
    description: str
    related_terms: tuple[str, ...] = ()
    evidence_links: tuple[str, ...] = ()
    taxon_id: Optional[str] = None
    status: str = "active"
    version: str = CONCEPT_VERSION

    def signature(self) -> str:
        return hash_obj({"concept_id": self.concept_id, "name": self.name,
                         "description": self.description, "related_terms": list(self.related_terms),
                         "evidence_links": list(self.evidence_links), "taxon_id": self.taxon_id,
                         "status": self.status})

    def to_dict(self) -> dict:
        return {"concept_id": self.concept_id, "name": self.name, "description": self.description,
                "related_terms": list(self.related_terms), "evidence_links": list(self.evidence_links),
                "taxon_id": self.taxon_id, "status": self.status, "version": self.version,
                "signature": self.signature()}


@dataclass(frozen=True)
class TaxonomyNode:
    """A node in the hierarchical taxonomy."""

    taxon_id: str
    name: str
    category: str               # clinical|eeg|finding|interpretation|knowledge|relationship
    parent_id: Optional[str]
    depth: int = 0
    version: str = TAXONOMY_VERSION

    def signature(self) -> str:
        return hash_obj({"taxon_id": self.taxon_id, "name": self.name, "category": self.category,
                         "parent_id": self.parent_id, "depth": self.depth})

    def to_dict(self) -> dict:
        return {"taxon_id": self.taxon_id, "name": self.name, "category": self.category,
                "parent_id": self.parent_id, "depth": self.depth, "version": self.version,
                "signature": self.signature()}


@dataclass(frozen=True)
class RelationshipRecord:
    """A versioned, typed edge between two registered knowledge/clinical entities."""

    relation_id: str
    subject_id: str
    subject_kind: str
    predicate: str
    object_id: str
    object_kind: str
    status: str = "active"
    lineage_id: Optional[str] = None
    version: str = RELATIONSHIP_VERSION

    def signature(self) -> str:
        return hash_obj({"relation_id": self.relation_id, "subject_id": self.subject_id,
                         "predicate": self.predicate, "object_id": self.object_id,
                         "status": self.status})

    def to_dict(self) -> dict:
        return {"relation_id": self.relation_id, "subject_id": self.subject_id,
                "subject_kind": self.subject_kind, "predicate": self.predicate,
                "object_id": self.object_id, "object_kind": self.object_kind, "status": self.status,
                "lineage_id": self.lineage_id, "version": self.version, "signature": self.signature()}


@dataclass(frozen=True)
class KnowledgeEvidenceLink:
    """A link from a knowledge artifact (concept/term) to registered evidence."""

    knowledge_id: str
    evidence_ref: str
    evidence_kind: str
    version: str = KNOWLEDGE_EVIDENCE_VERSION

    def to_dict(self) -> dict:
        return {"knowledge_id": self.knowledge_id, "evidence_ref": self.evidence_ref,
                "evidence_kind": self.evidence_kind, "version": self.version}


@dataclass(frozen=True)
class KnowledgeVersion:
    """A content-addressed knowledge-base version (chained: state + previous)."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


@dataclass(frozen=True)
class KnowledgeAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at}


@dataclass(frozen=True)
class KnowledgeLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class KnowledgeRegistryRecord:
    """Snapshot of the knowledge base for the registry."""

    version: str
    n_terms: int
    n_concepts: int
    n_taxonomy_nodes: int
    n_relationships: int
    n_evidence_links: int
    lineage_id: str
    audit_state: str
    knowledge_registry_version: str = KNOWLEDGE_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"version": self.version, "n_terms": self.n_terms,
                         "n_concepts": self.n_concepts, "n_taxonomy_nodes": self.n_taxonomy_nodes,
                         "n_relationships": self.n_relationships, "n_evidence_links": self.n_evidence_links,
                         "lineage_id": self.lineage_id})

    def to_dict(self) -> dict:
        return {"version": self.version, "n_terms": self.n_terms, "n_concepts": self.n_concepts,
                "n_taxonomy_nodes": self.n_taxonomy_nodes, "n_relationships": self.n_relationships,
                "n_evidence_links": self.n_evidence_links, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "knowledge_registry_version": self.knowledge_registry_version,
                "content_signature": self.content_signature()}
