# V2-P4 — Clinical Knowledge Layer (design & contracts)

> **Phase:** V2-P4 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0004`](../../../.gcc/decisions/ADR-0004-v2-p3-p4-findings-and-knowledge.md)

---

## 1. Knowledge is data, not code

The default knowledge base is a **declarative seed** (`seed.py`) — plain data —
loaded through governed `KnowledgeService` methods. Editing knowledge means editing
data + re-seeding, never changing logic. Nothing is hidden in code.

## 2. Terminology / Concepts / Taxonomy

- **Terms**: versioned (term, definition, source, status, related terms). Examples:
  IIC, LPD, GPD, LRDA, GRDA, Seizure, Background Activity, Artifact, Calibration,
  Coverage, Risk, Finding, Interpretation.
- **Concepts**: versioned, related to terms + evidence + a taxon.
- **Taxonomy**: a hierarchy across 6 categories (clinical / eeg / finding /
  interpretation / knowledge / relationship). Consistency is enforced: parents
  exist, depth = parent depth + 1, and the graph is acyclic.

## 3. Ontology (practical, not a reasoner)

Records the schema (entity kinds + which predicates connect which kinds) and a
small set of executable constraints (concept must relate to ≥ 1 term; relationship
endpoint kinds must match the predicate schema; taxonomy must be consistent;
evidence/term endpoints must be registered). Deliberately not overengineered.

## 4. Relationships

Typed, versioned, endpoint-validated edges. They connect the knowledge graph to the
clinical graph (Finding → Concept, Interpretation → Concept, …) and within knowledge
(concept_has_term, concept_in_taxon). A relationship's lineage node parents **both**
endpoints — so a `verify_chain` from a `finding_describes_concept` node spans the
clinical + knowledge graphs end to end.

## 5. Governance

A single immutable hash-chained audit log; content-addressed lineage with a moving
head; a chained knowledge-base version; versioned registry snapshots (no silent
overwrite). Validation runs 7 checks: terminology, taxonomy, ontology, relationship,
registry, lineage, audit integrity. Six reports: summary, terminology, concept,
taxonomy, relationship, validation.

## 6. Boundaries

Descriptive knowledge only — no diagnosis engine, no decision support, no treatment
logic (forbidden / later phases). Imports `ml` + `backend.clinical_cases`; never
`frontend`.
