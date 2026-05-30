"""Knowledge workspace — render registered knowledge artifacts as Page view-models."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, validation_badges
from ..visualizations import knowledge_relationships


def knowledge_pages(state) -> list:
    k = state.knowledge
    if not k:
        return [Page("knowledge", "Knowledge", [kv_panel("Knowledge", {"available": False})], [])]
    terminology = k.get("terminology", {})
    concepts = k.get("concepts", {})
    taxonomy = k.get("taxonomy", {})
    relationships = k.get("relationships", {})
    audit = k.get("audit", {})

    term_rows = []
    terms = terminology.get("terms", {})
    for tid, rec in (terms.items() if isinstance(terms, dict) else []):
        term_rows.append([tid[:16], rec.get("term"), (rec.get("definition") or "")[:48]])

    concept_rows = []
    cs = concepts.get("concepts", {})
    for cid, rec in (cs.items() if isinstance(cs, dict) else []):
        concept_rows.append([cid[:16], rec.get("name"), rec.get("status"),
                             len(rec.get("related_terms", [])), len(rec.get("evidence_links", []))])

    taxon_rows = []
    nodes = taxonomy.get("nodes", {})
    for tid, rec in (nodes.items() if isinstance(nodes, dict) else []):
        taxon_rows.append([tid[:16], rec.get("name"), rec.get("category"), rec.get("parent_id")])

    sections = [
        kv_panel("Knowledge Registry", {
            "n_concepts": concepts.get("n_concepts"),
            "n_terms": terminology.get("n_terms"),
            "n_taxa": taxonomy.get("n_nodes"),
            "n_relationships": relationships.get("n_relations"),
            "registry_version": k.get("registry", {}).get("knowledge_registry_version"),
        }),
        table("Terminology", ["term_id", "term", "definition"], term_rows),
        table("Concepts", ["concept_id", "name", "status", "n_terms", "n_evidence"], concept_rows),
        table("Taxonomies", ["taxon_id", "name", "category", "parent"], taxon_rows),
        table("Relationships", ["relation_id", "from", "relation", "to"],
              [[rid[:14], (rec.get("source_id") or rec.get("from") or "")[:14],
                rec.get("relation") or rec.get("predicate") or rec.get("kind"),
                (rec.get("target_id") or rec.get("to") or "")[:14]]
               for rid, rec in (relationships.get("relations", {}).items()
                                if isinstance(relationships.get("relations"), dict) else [])]),
        validation_badges("Knowledge Validation", k.get("validation", {})),
        badges("Knowledge Audit", [("audit_verified", audit.get("verified", False))]),
        table("Knowledge Audit Events", ["seq", "event", "hash"],
              [[e.get("seq"), e.get("kind"), e.get("event_hash", "")[:8]]
               for e in audit.get("events", [])]),
    ]
    viz = [knowledge_relationships(relationships)]
    return [Page("knowledge", "Knowledge", sections, viz)]
