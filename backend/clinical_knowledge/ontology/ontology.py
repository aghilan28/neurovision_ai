"""A practical ontology: entity kinds, relationship schema, and constraints.

The ontology records the *schema* of the knowledge graph (which entity kinds exist,
which predicates connect which kinds) and a small set of executable **constraints**
used to validate consistency. It deliberately avoids a heavyweight reasoner.
"""

from __future__ import annotations

from typing import Any

from ..version import ONTOLOGY_VERSION
from ..relationships import PREDICATES

ONTOLOGY_ENTITIES = ("term", "concept", "taxon", "relation",
                     "finding", "evidence", "interpretation", "case", "review")


class OntologyError(ValueError):
    """Raised on an ontology constraint violation."""


class Ontology:
    """Schema + constraints for the knowledge graph."""

    version = ONTOLOGY_VERSION

    def __init__(self) -> None:
        # mappings: predicate -> (subject_kind, object_kind); dependencies derived from these
        self.relationship_schema = dict(PREDICATES)
        self.entities = ONTOLOGY_ENTITIES

    def schema(self) -> dict:
        return {
            "ontology_version": ONTOLOGY_VERSION,
            "entities": list(self.entities),
            "relationships": {p: {"subject": s, "object": o}
                              for p, (s, o) in sorted(self.relationship_schema.items())},
            "constraints": [
                "every concept must relate to >= 1 term (concept_has_term)",
                "every relationship endpoint kind must match its predicate schema",
                "taxonomy must be a consistent acyclic hierarchy",
                "evidence-grounding predicates must reference registered evidence",
            ],
        }

    def validate(self, *, concepts: Any, terminology: Any, taxonomy: Any, relationships: Any) -> tuple[bool, list]:
        """Check the knowledge base against the ontology constraints."""
        violations: list[str] = []

        # constraint: relationship endpoint kinds match the schema
        for rid in relationships.list_relations():
            rel = relationships.get(rid)
            exp = self.relationship_schema.get(rel.predicate)
            if exp is None:
                violations.append(f"relation {rid}: unknown predicate {rel.predicate}")
            elif (rel.subject_kind, rel.object_kind) != exp:
                violations.append(f"relation {rid}: endpoints {(rel.subject_kind, rel.object_kind)} "
                                  f"!= schema {exp}")

        # constraint: every concept relates to >= 1 term (via related_terms or concept_has_term)
        term_rels = {(r.subject_id, r.object_id) for r in relationships.by_predicate("concept_has_term")}
        for cid in concepts.list_concepts():
            c = concepts.get(cid)
            has_term = bool(c.related_terms) or any(s == cid for (s, _) in term_rels)
            if not has_term:
                violations.append(f"concept {cid} has no related term (concept_has_term)")

        # constraint: taxonomy consistency
        ok, detail = taxonomy.check_consistency()
        if not ok:
            violations.append(f"taxonomy inconsistent: {detail}")

        # constraint: concept_in_taxon objects must be registered taxa
        for r in relationships.by_predicate("concept_in_taxon"):
            if not taxonomy.exists(r.object_id):
                violations.append(f"concept_in_taxon {r.relation_id}: taxon {r.object_id} not registered")

        # constraint: knowledge_uses_terminology / concept_has_term objects must be registered terms
        for pred in ("concept_has_term", "knowledge_uses_terminology"):
            for r in relationships.by_predicate(pred):
                if not terminology.exists(r.object_id):
                    violations.append(f"{pred} {r.relation_id}: term {r.object_id} not registered")

        return (len(violations) == 0), violations
