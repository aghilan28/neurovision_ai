"""Terminology registry: versioned terms (term, definition, source, status, relations)."""

from __future__ import annotations

from ..version import TERMINOLOGY_VERSION
from ..models.domain import Term
from ..identity import mint_term


class TerminologyRegistry:
    """In-memory terminology registry keyed by ``term_id``."""

    def __init__(self) -> None:
        self._terms: dict[str, Term] = {}

    def add(self, *, term: str, definition: str, source: str,
            related_terms: tuple = (), status: str = "active") -> Term:
        if not term or not definition:
            raise ValueError("term and definition are required")
        tid = mint_term(term, source)
        record = Term(term_id=tid, term=term, definition=definition, source=source,
                      status=status, related_terms=tuple(related_terms))
        self._terms[tid] = record
        return record

    def get(self, term_id: str) -> Term:
        if term_id not in self._terms:
            raise KeyError(f"term {term_id!r} not in registry")
        return self._terms[term_id]

    def exists(self, term_id: str) -> bool:
        return term_id in self._terms

    def list_terms(self) -> list[str]:
        return sorted(self._terms)

    def signature(self) -> str:
        from ml.provenance import hash_obj
        return hash_obj({tid: self._terms[tid].signature() for tid in sorted(self._terms)})

    def to_dict(self) -> dict:
        return {"terminology_version": TERMINOLOGY_VERSION, "n_terms": len(self._terms),
                "terms": {tid: t.to_dict() for tid, t in sorted(self._terms.items())}}
