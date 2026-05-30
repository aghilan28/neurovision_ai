"""KnowledgeService — the governed orchestration hub for the Clinical Knowledge Layer.

Ties terminology, concepts, taxonomy, ontology, relationships, evidence, registry,
audit, and lineage into the use cases that build and evolve the knowledge base, and
that connect knowledge to the clinical graph (e.g. Finding → Concept). Every
mutation is audited (immutable) → lineage-extended → version-bumped (chained) →
registry-snapshotted.

The knowledge base is data, not logic: it models terminology/concepts/relationships
and never performs diagnosis or decision support.
"""

from __future__ import annotations

from typing import Optional

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import CLINICAL_KNOWLEDGE_VERSION, DETERMINISTIC_EPOCH
from .models.domain import KnowledgeVersion, KnowledgeRegistryRecord, KnowledgeEvidenceLink
from .terminology import TerminologyRegistry
from .concepts import ConceptRegistry
from .taxonomy import Taxonomy
from .ontology import Ontology
from .relationships import RelationshipRegistry
from .evidence import KnowledgeEvidenceManager
from .audit import make_knowledge_audit_log
from .registry import KnowledgeRegistry
from .validation import KnowledgeValidator
from .lineage import (
    make_knowledge_source_lineage, make_term_lineage, make_concept_lineage,
    make_taxon_lineage, make_relationship_lineage,
)
from .reports import (
    build_knowledge_summary_report, build_concept_report, build_terminology_report,
    build_taxonomy_report, build_relationship_report, build_knowledge_validation_report,
)
from . import seed as seed_data
from ml.provenance import hash_obj


class KnowledgeService:
    """Stateful service holding the knowledge base + shared lineage tracker."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 source_name: str = "knowledge-base", source_version: str = "1.0.0",
                 created_at: str = DETERMINISTIC_EPOCH):
        self.lineage = lineage_tracker or LineageTracker()
        self.terminology = TerminologyRegistry()
        self.concepts = ConceptRegistry()
        self.taxonomy = Taxonomy()
        self.ontology = Ontology()
        self.relationships = RelationshipRegistry()
        self.evidence = KnowledgeEvidenceManager()
        self.registry = KnowledgeRegistry()
        self.validator = KnowledgeValidator()
        self.audit = make_knowledge_audit_log()
        self._evidence_links: list = []
        # lineage node maps (knowledge_id -> lineage node id)
        self._term_nodes: dict[str, str] = {}
        self._concept_nodes: dict[str, str] = {}
        self._taxon_nodes: dict[str, str] = {}

        from .identity import mint_knowledge_source
        sid = mint_knowledge_source(source_name, source_version)
        node = self.lineage.record(make_knowledge_source_lineage(sid, created_at=created_at))
        self._source_lineage = node.lineage_id
        self._head = node.lineage_id
        self.audit.append("knowledge_source", {"source_id": sid, "name": source_name,
                                               "version": source_version}, created_at=created_at)
        self._version = KnowledgeVersion(version="", previous=None, reason="init", created_at=created_at)
        self._commit(reason="init", created_at=created_at)

    @property
    def version(self) -> str:
        return self._version.version

    @property
    def head_lineage_id(self) -> str:
        return self._head

    # --- terminology / concepts / taxonomy ------------------------------------
    def add_term(self, *, term: str, definition: str, source: str, related_terms: tuple = (),
                 created_at: str = DETERMINISTIC_EPOCH):
        rec = self.terminology.add(term=term, definition=definition, source=source,
                                   related_terms=related_terms)
        node = self.lineage.record(make_term_lineage(rec.term_id, source_lineage_id=self._source_lineage,
                                                     created_at=created_at))
        self._term_nodes[rec.term_id] = node.lineage_id
        self.audit.append("term_added", rec.to_dict(), created_at=created_at)
        self._advance(node.lineage_id, created_at)
        self._commit(reason=f"term:{rec.term_id}", created_at=created_at)
        return rec

    def add_taxon(self, *, name: str, category: str, parent_id: Optional[str] = None,
                  created_at: str = DETERMINISTIC_EPOCH):
        rec = self.taxonomy.add(name=name, category=category, parent_id=parent_id)
        parent_node = self._taxon_nodes.get(parent_id, self._source_lineage)
        node = self.lineage.record(make_taxon_lineage(rec.taxon_id, parent_lineage_id=parent_node,
                                                      created_at=created_at))
        self._taxon_nodes[rec.taxon_id] = node.lineage_id
        self.audit.append("taxon_added", rec.to_dict(), created_at=created_at)
        self._advance(node.lineage_id, created_at)
        self._commit(reason=f"taxon:{rec.taxon_id}", created_at=created_at)
        return rec

    def add_concept(self, *, name: str, description: str, related_terms: tuple = (),
                    evidence_links: tuple = (), taxon_id: Optional[str] = None,
                    created_at: str = DETERMINISTIC_EPOCH):
        rec = self.concepts.add(name=name, description=description, related_terms=related_terms,
                                evidence_links=evidence_links, taxon_id=taxon_id)
        term_nodes = tuple(self._term_nodes[t] for t in related_terms if t in self._term_nodes)
        node = self.lineage.record(make_concept_lineage(rec.concept_id,
                                                        source_lineage_id=self._source_lineage,
                                                        term_lineage_ids=term_nodes, created_at=created_at))
        self._concept_nodes[rec.concept_id] = node.lineage_id
        self.audit.append("concept_added", rec.to_dict(), created_at=created_at)
        self._advance(node.lineage_id, created_at)
        # auto-relationships: concept_has_term, concept_in_taxon (governed edges)
        for tid in related_terms:
            self._add_relationship(rec.concept_id, "concept_has_term", tid,
                                   self._concept_nodes[rec.concept_id], self._term_nodes.get(tid), created_at)
        if taxon_id:
            self._add_relationship(rec.concept_id, "concept_in_taxon", taxon_id,
                                   self._concept_nodes[rec.concept_id], self._taxon_nodes.get(taxon_id), created_at)
        self._commit(reason=f"concept:{rec.concept_id}", created_at=created_at)
        return rec

    # --- relationships --------------------------------------------------------
    def add_relationship(self, *, subject_id: str, predicate: str, object_id: str,
                         subject_lineage_id: Optional[str] = None, object_lineage_id: Optional[str] = None,
                         created_at: str = DETERMINISTIC_EPOCH):
        rec = self._add_relationship(subject_id, predicate, object_id,
                                     subject_lineage_id or self._lineage_of(subject_id),
                                     object_lineage_id or self._lineage_of(object_id), created_at)
        self._commit(reason=f"relationship:{rec.relation_id}", created_at=created_at)
        return rec

    def link_finding_to_concept(self, *, finding_id: str, concept_id: str, finding_lineage_id: str,
                                created_at: str = DETERMINISTIC_EPOCH):
        """Connect the clinical graph to the knowledge graph (Finding → Concept)."""
        return self.add_relationship(subject_id=finding_id, predicate="finding_describes_concept",
                                     object_id=concept_id, subject_lineage_id=finding_lineage_id,
                                     object_lineage_id=self._concept_nodes.get(concept_id),
                                     created_at=created_at)

    def link_interpretation_to_concept(self, *, interpretation_id: str, concept_id: str,
                                       interpretation_lineage_id: str,
                                       created_at: str = DETERMINISTIC_EPOCH):
        return self.add_relationship(subject_id=interpretation_id, predicate="interpretation_refers_concept",
                                     object_id=concept_id, subject_lineage_id=interpretation_lineage_id,
                                     object_lineage_id=self._concept_nodes.get(concept_id),
                                     created_at=created_at)

    def ground_concept_in_evidence(self, *, concept_id: str, evidence_ref: str, evidence_kind: str,
                                   evidence_lineage_id: Optional[str] = None,
                                   created_at: str = DETERMINISTIC_EPOCH):
        self.concepts.attach_evidence(concept_id, evidence_ref)
        link = self.evidence.link(knowledge_id=concept_id, evidence_ref=evidence_ref,
                                  evidence_kind=evidence_kind)
        self._evidence_links.append(link)
        self.audit.append("evidence_linked", link.to_dict(), created_at=created_at)
        rec = self._add_relationship(concept_id, "knowledge_grounded_in_evidence", evidence_ref,
                                     self._concept_nodes.get(concept_id), evidence_lineage_id, created_at)
        self._commit(reason=f"evidence:{concept_id}", created_at=created_at)
        return rec

    # --- seed -----------------------------------------------------------------
    def seed_default_knowledge(self, created_at: str = DETERMINISTIC_EPOCH) -> "KnowledgeService":
        """Load the declarative default knowledge (data) into the governed registries."""
        taxon_ids: dict[tuple, str] = {}
        for category, name, parent_name in seed_data.TAXONOMY:
            parent_id = taxon_ids.get((category, parent_name)) if parent_name else None
            rec = self.add_taxon(name=name, category=category, parent_id=parent_id, created_at=created_at)
            taxon_ids[(category, name)] = rec.taxon_id
        term_ids: dict[str, str] = {}
        for term, definition, source in seed_data.TERMS:
            rec = self.add_term(term=term, definition=definition, source=source, created_at=created_at)
            term_ids[term] = rec.term_id
        for name, description, term_names, taxon_key in seed_data.CONCEPTS:
            related = tuple(term_ids[t] for t in term_names if t in term_ids)
            taxon_id = taxon_ids.get(tuple(taxon_key)) if taxon_key else None
            self.add_concept(name=name, description=description, related_terms=related,
                             taxon_id=taxon_id, created_at=created_at)
        return self

    def concept_by_name(self, name: str) -> Optional[str]:
        for cid in self.concepts.list_concepts():
            if self.concepts.get(cid).name == name:
                return cid
        return None

    # --- validation + reports -------------------------------------------------
    def validate(self):
        return self.validator.validate(
            terminology=self.terminology, concepts=self.concepts, taxonomy=self.taxonomy,
            ontology=self.ontology, relationships=self.relationships, registry=self.registry,
            audit_log=self.audit, lineage_tracker=self.lineage, head_lineage_id=self._head,
            version=self.version)

    def reports(self) -> dict:
        validation = self.validate().to_dict()
        kw = {"version": self.version, "head_lineage_id": self._head}
        return {
            "knowledge_summary_report": build_knowledge_summary_report(
                **kw, terminology=self.terminology, concepts=self.concepts,
                taxonomy=self.taxonomy, relationships=self.relationships),
            "terminology_report": build_terminology_report(**kw, terminology=self.terminology),
            "concept_report": build_concept_report(**kw, concepts=self.concepts),
            "taxonomy_report": build_taxonomy_report(**kw, taxonomy=self.taxonomy),
            "relationship_report": build_relationship_report(**kw, relationships=self.relationships),
            "knowledge_validation_report": build_knowledge_validation_report(
                **kw, validation_report_dict=validation),
        }

    # --- internals ------------------------------------------------------------
    def _add_relationship(self, subject_id, predicate, object_id, subject_lineage_id,
                          object_lineage_id, created_at):
        rec = self.relationships.add(subject_id=subject_id, predicate=predicate, object_id=object_id)
        node = self.lineage.record(make_relationship_lineage(
            rec.relation_id, subject_lineage_id=subject_lineage_id, object_lineage_id=object_lineage_id,
            created_at=created_at))
        from dataclasses import replace
        rec = replace(rec, lineage_id=node.lineage_id)
        # store the lineage-tagged record back into the registry
        self.relationships._relations[rec.relation_id] = rec
        self.audit.append("relationship_added", rec.to_dict(), created_at=created_at)
        self._advance(node.lineage_id, created_at)
        return rec

    def _lineage_of(self, entity_id: str) -> Optional[str]:
        return (self._concept_nodes.get(entity_id) or self._term_nodes.get(entity_id)
                or self._taxon_nodes.get(entity_id))

    def _advance(self, node_id: str, created_at: str) -> None:
        from .lineage import make_lineage_record, knowledge_version_bundle
        node = self.lineage.record(make_lineage_record(
            kind="knowledge", versions=knowledge_version_bundle(),
            inputs={"head": self._head}, outputs={"included": node_id},
            parents=(self._head, node_id), created_at=created_at))
        self._head = node.lineage_id

    def _state_signature(self) -> str:
        return hash_obj({"terminology": self.terminology.signature(),
                         "concepts": self.concepts.signature(),
                         "taxonomy": self.taxonomy.signature(),
                         "relationships": self.relationships.signature()})

    def _commit(self, *, reason: str, created_at: str) -> None:
        previous = self._version.version or None
        self._version = KnowledgeVersion(
            version=KnowledgeVersion.compute(self._state_signature(), previous),
            previous=previous, reason=reason, created_at=created_at)
        self.audit.append("version_changed", {"version": self._version.version, "reason": reason},
                          created_at=created_at)
        self.registry.register(KnowledgeRegistryRecord(
            version=self._version.version, n_terms=len(self.terminology.list_terms()),
            n_concepts=len(self.concepts.list_concepts()),
            n_taxonomy_nodes=len(self.taxonomy.list_nodes()),
            n_relationships=len(self.relationships.list_relations()),
            n_evidence_links=len(self._evidence_links), lineage_id=self._head,
            audit_state=self.audit.head))
