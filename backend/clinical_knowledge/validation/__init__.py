"""``backend/clinical_knowledge/validation`` — knowledge validation (V2-P4).

The mandated integrity checks: terminology, taxonomy, ontology, relationship,
registry, lineage, audit. Reuses ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from .validators import KnowledgeValidator, KnowledgeValidationError

__all__ = ["KnowledgeValidator", "KnowledgeValidationError"]
