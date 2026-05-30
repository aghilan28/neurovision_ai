"""Typed, versioned relationship registry.

Relationships are the edges that connect the knowledge graph to the clinical object
graph (findings, interpretations, cases, reviews, evidence) and within knowledge
(concept↔term, concept↔taxon). Each predicate declares its expected
subject/object *kinds*; endpoints are validated on registration.
"""

from __future__ import annotations

from typing import Optional

from ..version import RELATIONSHIP_VERSION
from ..models.domain import RelationshipRecord
from ..identity import mint_relation

# predicate -> (subject_kind, object_kind). The mandated relationship types plus
# the intra-knowledge edges. Kinds are validated against id prefixes where the id
# is content-addressed (term/concept/taxon/relation); free-form clinical ids
# (finding/case/review/evidence/interpretation) are validated by prefix too.
PREDICATES: dict[str, tuple[str, str]] = {
    "finding_describes_concept": ("finding", "concept"),
    "finding_supported_by_evidence": ("finding", "evidence"),
    "interpretation_refers_concept": ("interpretation", "concept"),
    "case_has_finding": ("case", "finding"),
    "review_produced_finding": ("review", "finding"),
    "knowledge_grounded_in_evidence": ("concept", "evidence"),
    "knowledge_uses_terminology": ("concept", "term"),
    "concept_has_term": ("concept", "term"),
    "concept_in_taxon": ("concept", "taxon"),
}

PREDICATE_SIGNATURES = tuple(sorted(PREDICATES))


class RelationshipError(ValueError):
    """Raised on an invalid relationship operation."""


def _kind_of(entity_id: str) -> str:
    return entity_id.split("+", 1)[0] if "+" in entity_id else "?"


class RelationshipRegistry:
    """In-memory relationship registry keyed by ``relation_id``."""

    def __init__(self) -> None:
        self._relations: dict[str, RelationshipRecord] = {}

    def add(self, *, subject_id: str, predicate: str, object_id: str,
            lineage_id: Optional[str] = None, status: str = "active") -> RelationshipRecord:
        if predicate not in PREDICATES:
            raise RelationshipError(f"unknown predicate {predicate!r}; allowed: {PREDICATE_SIGNATURES}")
        exp_subj, exp_obj = PREDICATES[predicate]
        subj_kind, obj_kind = _kind_of(subject_id), _kind_of(object_id)
        if subj_kind != exp_subj:
            raise RelationshipError(f"{predicate}: subject must be {exp_subj!r}, got {subj_kind!r}")
        if obj_kind != exp_obj:
            raise RelationshipError(f"{predicate}: object must be {exp_obj!r}, got {obj_kind!r}")
        rid = mint_relation(subject_id, predicate, object_id)
        record = RelationshipRecord(relation_id=rid, subject_id=subject_id, subject_kind=subj_kind,
                                    predicate=predicate, object_id=object_id, object_kind=obj_kind,
                                    status=status, lineage_id=lineage_id)
        self._relations[rid] = record
        return record

    def get(self, relation_id: str) -> RelationshipRecord:
        if relation_id not in self._relations:
            raise KeyError(f"relation {relation_id!r} not in registry")
        return self._relations[relation_id]

    def exists(self, relation_id: str) -> bool:
        return relation_id in self._relations

    def list_relations(self) -> list[str]:
        return sorted(self._relations)

    def by_predicate(self, predicate: str) -> list[RelationshipRecord]:
        return [r for r in self._relations.values() if r.predicate == predicate]

    def by_subject(self, subject_id: str) -> list[RelationshipRecord]:
        return [r for r in self._relations.values() if r.subject_id == subject_id]

    def signature(self) -> str:
        from ml.provenance import hash_obj
        return hash_obj({rid: self._relations[rid].signature() for rid in sorted(self._relations)})

    def to_dict(self) -> dict:
        return {"relationship_version": RELATIONSHIP_VERSION, "n_relationships": len(self._relations),
                "predicates": list(PREDICATE_SIGNATURES),
                "relationships": {rid: r.to_dict() for rid, r in sorted(self._relations.items())}}
