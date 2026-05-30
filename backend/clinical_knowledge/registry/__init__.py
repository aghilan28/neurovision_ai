"""``backend/clinical_knowledge/registry`` — the knowledge registry (V2-P4).

Aggregates the knowledge base (concepts, terms, taxonomies, relationships, evidence
links) with versions and audit/lineage references. Snapshots are versioned and
reject silent overwrite.
"""

from __future__ import annotations

from .registry import KnowledgeRegistry

__all__ = ["KnowledgeRegistry"]
