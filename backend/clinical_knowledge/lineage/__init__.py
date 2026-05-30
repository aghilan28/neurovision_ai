"""``backend/clinical_knowledge/lineage`` — knowledge lineage (V2-P4).

Content-addressed lineage nodes for knowledge artifacts (source/concept/term/
taxon/relation) on ``ml.lineage``. Relationship nodes parent to their subject +
object nodes, connecting the knowledge graph to the clinical graph (shared tracker).
"""

from __future__ import annotations

from .lineage import (
    knowledge_version_bundle,
    make_knowledge_source_lineage,
    make_term_lineage,
    make_concept_lineage,
    make_taxon_lineage,
    make_relationship_lineage,
)
from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

__all__ = ["knowledge_version_bundle", "make_knowledge_source_lineage", "make_term_lineage",
           "make_concept_lineage", "make_taxon_lineage", "make_relationship_lineage",
           "make_lineage_record", "LineageRecord"]
