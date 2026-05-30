"""Clinical-knowledge lineage helpers built on ml.lineage."""

from __future__ import annotations

from typing import Optional

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    CLINICAL_KNOWLEDGE_VERSION, KNOWLEDGE_DOMAIN_VERSION, KNOWLEDGE_IDENTITY_VERSION,
    KNOWLEDGE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def knowledge_version_bundle(**extra: object) -> dict:
    bundle = {
        "clinical_knowledge_version": CLINICAL_KNOWLEDGE_VERSION,
        "knowledge_domain_version": KNOWLEDGE_DOMAIN_VERSION,
        "knowledge_identity_version": KNOWLEDGE_IDENTITY_VERSION,
        "knowledge_lineage_version": KNOWLEDGE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_knowledge_source_lineage(source_id: str, *, parent: Optional[str] = None,
                                  created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="knowledge", versions=knowledge_version_bundle(),
                               inputs={"source_id": source_id}, outputs={"source_id": source_id},
                               parents=(parent,) if parent else (), created_at=created_at)


def make_term_lineage(term_id: str, *, source_lineage_id: str, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="term", versions=knowledge_version_bundle(),
                               inputs={"term_id": term_id}, outputs={"term_id": term_id},
                               parents=(source_lineage_id,), created_at=created_at)


def make_concept_lineage(concept_id: str, *, source_lineage_id: str, term_lineage_ids: tuple = (),
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="concept", versions=knowledge_version_bundle(),
                               inputs={"concept_id": concept_id}, outputs={"concept_id": concept_id},
                               parents=(source_lineage_id,) + tuple(term_lineage_ids), created_at=created_at)


def make_taxon_lineage(taxon_id: str, *, parent_lineage_id: str, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="taxon", versions=knowledge_version_bundle(),
                               inputs={"taxon_id": taxon_id}, outputs={"taxon_id": taxon_id},
                               parents=(parent_lineage_id,), created_at=created_at)


def make_relationship_lineage(relation_id: str, *, subject_lineage_id: Optional[str],
                              object_lineage_id: Optional[str],
                              created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A relationship node parents to both endpoints' lineage nodes (connects graphs)."""
    parents = tuple(p for p in (subject_lineage_id, object_lineage_id) if p)
    return make_lineage_record(kind="relation", versions=knowledge_version_bundle(),
                               inputs={"relation_id": relation_id}, outputs={"relation_id": relation_id},
                               parents=parents, created_at=created_at)
