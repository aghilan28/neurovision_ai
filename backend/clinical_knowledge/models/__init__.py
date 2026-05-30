"""``backend/clinical_knowledge/models`` — the Knowledge domain model (V2-P4).

Structured clinical knowledge entities: Term, Concept, TaxonomyNode,
RelationshipRecord, plus version/audit/lineage/registry projections. Knowledge is
data — versioned, auditable, explainable — never logic hidden in code, and never a
diagnosis engine.
"""

from __future__ import annotations

from .domain import (
    Term,
    Concept,
    TaxonomyNode,
    RelationshipRecord,
    KnowledgeEvidenceLink,
    KnowledgeVersion,
    KnowledgeAuditRecord,
    KnowledgeLineageRecord,
    KnowledgeRegistryRecord,
)

__all__ = [
    "Term",
    "Concept",
    "TaxonomyNode",
    "RelationshipRecord",
    "KnowledgeEvidenceLink",
    "KnowledgeVersion",
    "KnowledgeAuditRecord",
    "KnowledgeLineageRecord",
    "KnowledgeRegistryRecord",
]
