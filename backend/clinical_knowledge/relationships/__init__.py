"""``backend/clinical_knowledge/relationships`` — typed, versioned relationships (V2-P4)."""

from __future__ import annotations

from .relationships import RelationshipRegistry, PREDICATES, PREDICATE_SIGNATURES, RelationshipError

__all__ = ["RelationshipRegistry", "PREDICATES", "PREDICATE_SIGNATURES", "RelationshipError"]
