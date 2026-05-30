"""``backend/clinical_knowledge`` — Clinical Knowledge Layer (V2-P4).

Structured clinical knowledge: terminology, concepts, a hierarchical taxonomy, a
practical ontology, and typed relationships — versioned, traceable, auditable,
lineage-tracked, explainable, governed, extensible. Knowledge is **data, never
logic hidden in code**, and this layer is emphatically **not a diagnosis engine**
and contains **no decision support** (forbidden / belongs to V2-P6+).

It connects to the clinical graph via relationships (Finding → Concept,
Interpretation → Concept, Knowledge → Evidence, …), giving the deliverable chain its
"Knowledge Context".

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling ``backend.clinical_cases`` (audit primitive); integrates with the finding/
review/inference graphs via the shared lineage tracker. It never imports
``frontend``. See ``.gcc/decisions/ADR-0004``.
"""

from __future__ import annotations

from .version import (
    CLINICAL_KNOWLEDGE_VERSION, KNOWLEDGE_DOMAIN_VERSION, KNOWLEDGE_IDENTITY_VERSION,
    TERMINOLOGY_VERSION, CONCEPT_VERSION, TAXONOMY_VERSION, ONTOLOGY_VERSION,
    RELATIONSHIP_VERSION, KNOWLEDGE_REGISTRY_VERSION, KNOWLEDGE_AUDIT_VERSION,
    KNOWLEDGE_LINEAGE_VERSION, KNOWLEDGE_VALIDATION_VERSION, KNOWLEDGE_REPORT_VERSION,
)
from .models import (
    Term, Concept, TaxonomyNode, RelationshipRecord, KnowledgeEvidenceLink,
    KnowledgeVersion, KnowledgeAuditRecord, KnowledgeLineageRecord, KnowledgeRegistryRecord,
)
from .terminology import TerminologyRegistry
from .concepts import ConceptRegistry
from .taxonomy import Taxonomy, TAXONOMY_CATEGORIES, TaxonomyError
from .ontology import Ontology, ONTOLOGY_ENTITIES, OntologyError
from .relationships import RelationshipRegistry, PREDICATES, RelationshipError
from .registry import KnowledgeRegistry
from .audit import make_knowledge_audit_log
from .validation import KnowledgeValidator, KnowledgeValidationError
from .service import KnowledgeService

__all__ = [
    "CLINICAL_KNOWLEDGE_VERSION", "KNOWLEDGE_DOMAIN_VERSION", "KNOWLEDGE_IDENTITY_VERSION",
    "TERMINOLOGY_VERSION", "CONCEPT_VERSION", "TAXONOMY_VERSION", "ONTOLOGY_VERSION",
    "RELATIONSHIP_VERSION", "KNOWLEDGE_REGISTRY_VERSION", "KNOWLEDGE_AUDIT_VERSION",
    "KNOWLEDGE_LINEAGE_VERSION", "KNOWLEDGE_VALIDATION_VERSION", "KNOWLEDGE_REPORT_VERSION",
    "Term", "Concept", "TaxonomyNode", "RelationshipRecord", "KnowledgeEvidenceLink",
    "KnowledgeVersion", "KnowledgeAuditRecord", "KnowledgeLineageRecord", "KnowledgeRegistryRecord",
    "TerminologyRegistry", "ConceptRegistry", "Taxonomy", "TAXONOMY_CATEGORIES", "TaxonomyError",
    "Ontology", "ONTOLOGY_ENTITIES", "OntologyError",
    "RelationshipRegistry", "PREDICATES", "RelationshipError",
    "KnowledgeRegistry", "make_knowledge_audit_log",
    "KnowledgeValidator", "KnowledgeValidationError", "KnowledgeService",
]
