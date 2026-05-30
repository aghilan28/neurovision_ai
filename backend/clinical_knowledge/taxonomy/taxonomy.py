"""Hierarchical taxonomy with consistency validation.

Supports the mandated concept categories (clinical / EEG / finding / interpretation
/ knowledge / relationship). Enforces hierarchy consistency: parents must exist,
depth = parent.depth + 1, and the graph must be acyclic (a tree).
"""

from __future__ import annotations

from typing import Optional

from ..version import TAXONOMY_VERSION
from ..models.domain import TaxonomyNode
from ..identity import mint_taxon

TAXONOMY_CATEGORIES = ("clinical", "eeg", "finding", "interpretation", "knowledge", "relationship")


class TaxonomyError(ValueError):
    """Raised on an inconsistent taxonomy operation."""


class Taxonomy:
    """In-memory hierarchical taxonomy keyed by ``taxon_id``."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaxonomyNode] = {}

    def add(self, *, name: str, category: str, parent_id: Optional[str] = None) -> TaxonomyNode:
        if category not in TAXONOMY_CATEGORIES:
            raise TaxonomyError(f"category must be one of {TAXONOMY_CATEGORIES}")
        depth = 0
        if parent_id is not None:
            if parent_id not in self._nodes:
                raise TaxonomyError(f"parent taxon {parent_id!r} does not exist")
            depth = self._nodes[parent_id].depth + 1
        tid = mint_taxon(category, name, parent_id)
        if tid in self._nodes:
            return self._nodes[tid]
        node = TaxonomyNode(taxon_id=tid, name=name, category=category, parent_id=parent_id, depth=depth)
        self._nodes[tid] = node
        return node

    def get(self, taxon_id: str) -> TaxonomyNode:
        if taxon_id not in self._nodes:
            raise KeyError(f"taxon {taxon_id!r} not in taxonomy")
        return self._nodes[taxon_id]

    def exists(self, taxon_id: str) -> bool:
        return taxon_id in self._nodes

    def children(self, taxon_id: Optional[str]) -> list[str]:
        return sorted(tid for tid, n in self._nodes.items() if n.parent_id == taxon_id)

    def roots(self) -> list[str]:
        return self.children(None)

    def list_nodes(self) -> list[str]:
        return sorted(self._nodes)

    def check_consistency(self) -> tuple[bool, str]:
        """Return (ok, detail): parents exist, depths correct, and no cycles."""
        for tid, n in self._nodes.items():
            if n.parent_id is not None:
                if n.parent_id not in self._nodes:
                    return False, f"taxon {tid} has missing parent {n.parent_id}"
                if n.depth != self._nodes[n.parent_id].depth + 1:
                    return False, f"taxon {tid} has inconsistent depth"
            elif n.depth != 0:
                return False, f"root taxon {tid} must have depth 0"
        # acyclicity: walk parents to a root
        for tid in self._nodes:
            seen = set()
            cur = tid
            while cur is not None:
                if cur in seen:
                    return False, f"cycle detected at {tid}"
                seen.add(cur)
                cur = self._nodes[cur].parent_id
        return True, "consistent"

    def signature(self) -> str:
        from ml.provenance import hash_obj
        return hash_obj({tid: self._nodes[tid].signature() for tid in sorted(self._nodes)})

    def to_dict(self) -> dict:
        return {"taxonomy_version": TAXONOMY_VERSION, "n_nodes": len(self._nodes),
                "categories": list(TAXONOMY_CATEGORIES),
                "nodes": {tid: n.to_dict() for tid, n in sorted(self._nodes.items())}}
