"""``backend/clinical_knowledge/ontology`` — practical ontology layer (V2-P4).

Represents entities, relationships, constraints, mappings and dependencies — and
validates the knowledge base against them. Deliberately practical (no OWL/reasoner):
just enough structure to keep the knowledge base internally consistent.
"""

from __future__ import annotations

from .ontology import Ontology, ONTOLOGY_ENTITIES, OntologyError

__all__ = ["Ontology", "ONTOLOGY_ENTITIES", "OntologyError"]
