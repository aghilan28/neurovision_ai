"""Concept registry: versioned concepts related to terms, evidence, and taxonomy."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from ..version import CONCEPT_VERSION
from ..models.domain import Concept
from ..identity import mint_concept


class ConceptRegistry:
    """In-memory concept registry keyed by ``concept_id``."""

    def __init__(self) -> None:
        self._concepts: dict[str, Concept] = {}

    def add(self, *, name: str, description: str, related_terms: tuple = (),
            evidence_links: tuple = (), taxon_id: Optional[str] = None, status: str = "active") -> Concept:
        if not name or not description:
            raise ValueError("name and description are required")
        cid = mint_concept(name)
        record = Concept(concept_id=cid, name=name, description=description,
                         related_terms=tuple(related_terms), evidence_links=tuple(evidence_links),
                         taxon_id=taxon_id, status=status)
        self._concepts[cid] = record
        return record

    def attach_evidence(self, concept_id: str, evidence_ref: str) -> Concept:
        c = self.get(concept_id)
        merged = tuple(dict.fromkeys(c.evidence_links + (evidence_ref,)))
        c = replace(c, evidence_links=merged)
        self._concepts[concept_id] = c
        return c

    def set_taxon(self, concept_id: str, taxon_id: str) -> Concept:
        c = replace(self.get(concept_id), taxon_id=taxon_id)
        self._concepts[concept_id] = c
        return c

    def get(self, concept_id: str) -> Concept:
        if concept_id not in self._concepts:
            raise KeyError(f"concept {concept_id!r} not in registry")
        return self._concepts[concept_id]

    def exists(self, concept_id: str) -> bool:
        return concept_id in self._concepts

    def list_concepts(self) -> list[str]:
        return sorted(self._concepts)

    def signature(self) -> str:
        from ml.provenance import hash_obj
        return hash_obj({cid: self._concepts[cid].signature() for cid in sorted(self._concepts)})

    def to_dict(self) -> dict:
        return {"concept_version": CONCEPT_VERSION, "n_concepts": len(self._concepts),
                "concepts": {cid: c.to_dict() for cid, c in sorted(self._concepts.items())}}
