"""Tests for the Clinical Knowledge Layer (V2-P4).

Covers terminology, concepts, taxonomy consistency, ontology constraints,
relationships (typed/validated), registry, immutable audit, lineage, validation,
reports, and deterministic seeding.
"""

from __future__ import annotations

import pytest

from backend.clinical_knowledge import (
    KnowledgeService, Taxonomy, TaxonomyError, RelationshipRegistry, RelationshipError,
    Ontology, PREDICATES, TAXONOMY_CATEGORIES,
)
from backend.clinical_knowledge.identity import validate_identity


@pytest.fixture
def seeded():
    return KnowledgeService().seed_default_knowledge()


def test_seed_populates_registries(seeded):
    assert len(seeded.terminology.list_terms()) >= 11
    assert len(seeded.concepts.list_concepts()) >= 8
    assert len(seeded.taxonomy.list_nodes()) >= 6
    assert len(seeded.relationships.list_relations()) >= 8


def test_seed_is_deterministic():
    a = KnowledgeService().seed_default_knowledge()
    b = KnowledgeService().seed_default_knowledge()
    assert a.version == b.version
    assert a.terminology.signature() == b.terminology.signature()
    assert a.concepts.signature() == b.concepts.signature()


def test_terminology_ids_valid(seeded):
    for tid in seeded.terminology.list_terms():
        assert validate_identity(tid, "term")[0]


def test_taxonomy_consistency_and_categories(seeded):
    ok, detail = seeded.taxonomy.check_consistency()
    assert ok, detail
    cats = {seeded.taxonomy.get(t).category for t in seeded.taxonomy.list_nodes()}
    assert cats.issubset(set(TAXONOMY_CATEGORIES))


def test_taxonomy_rejects_missing_parent():
    tax = Taxonomy()
    with pytest.raises(TaxonomyError):
        tax.add(name="orphan", category="eeg", parent_id="taxon+" + "0" * 16)


def test_taxonomy_detects_inconsistency():
    tax = Taxonomy()
    root = tax.add(name="root", category="eeg")
    child = tax.add(name="child", category="eeg", parent_id=root.taxon_id)
    # tamper: corrupt the child's depth
    import dataclasses
    tax._nodes[child.taxon_id] = dataclasses.replace(tax._nodes[child.taxon_id], depth=5)
    ok, _ = tax.check_consistency()
    assert ok is False


def test_relationship_predicate_and_endpoint_validation():
    reg = RelationshipRegistry()
    with pytest.raises(RelationshipError):
        reg.add(subject_id="concept+" + "a" * 16, predicate="not_a_predicate",
                object_id="term+" + "b" * 16)
    # endpoint-kind mismatch (concept_has_term wants object kind 'term')
    with pytest.raises(RelationshipError):
        reg.add(subject_id="concept+" + "a" * 16, predicate="concept_has_term",
                object_id="concept+" + "b" * 16)


def test_ontology_validation_passes(seeded):
    ok, violations = seeded.ontology.validate(
        concepts=seeded.concepts, terminology=seeded.terminology,
        taxonomy=seeded.taxonomy, relationships=seeded.relationships)
    assert ok, violations
    schema = seeded.ontology.schema()
    assert set(PREDICATES).issubset(set(schema["relationships"]))


def test_knowledge_validation_all_checks(seeded):
    rep = seeded.validate()
    assert rep.ok, [c.to_dict() for c in rep.failures()]
    assert {c.name for c in rep.checks} == {
        "terminology_integrity", "taxonomy_integrity", "ontology_integrity",
        "relationship_integrity", "registry_integrity", "lineage_integrity", "audit_integrity"}


def test_knowledge_audit_tamper_evident(seeded):
    assert seeded.audit.verify()
    object.__setattr__(seeded.audit.events()[2], "payload", {"x": 1})
    assert seeded.audit.verify() is False


def test_knowledge_lineage_verifies(seeded):
    assert seeded.lineage.verify_chain(seeded.head_lineage_id)


def test_knowledge_registry_versioned_and_no_silent_overwrite(seeded):
    latest = seeded.registry.latest()
    assert latest.version == seeded.version
    from backend.clinical_knowledge.models import KnowledgeRegistryRecord
    tampered = KnowledgeRegistryRecord(version=latest.version, n_terms=999, n_concepts=0,
                                       n_taxonomy_nodes=0, n_relationships=0, n_evidence_links=0,
                                       lineage_id="lineage+" + "0" * 16, audit_state="h")
    with pytest.raises(ValueError):
        seeded.registry.register(tampered)


def test_knowledge_reports_generate(seeded):
    reps = seeded.reports()
    assert set(reps) == {"knowledge_summary_report", "terminology_report", "concept_report",
                         "taxonomy_report", "relationship_report", "knowledge_validation_report"}


def test_concept_lookup_by_name(seeded):
    cid = seeded.concept_by_name("Conformal Coverage")
    assert cid and seeded.concepts.get(cid).name == "Conformal Coverage"
