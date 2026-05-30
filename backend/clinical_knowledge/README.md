# `backend/clinical_knowledge/` — Clinical Knowledge Layer (V2-P4)

> **Layer:** Application (`backend/`) · **Status:** Implemented (V2-P4).
> **Decision record:** [`../../.gcc/decisions/ADR-0004`](../../.gcc/decisions/ADR-0004-v2-p3-p4-findings-and-knowledge.md)
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility),
> AP-7/NR-8 (boundaries)

Structured clinical knowledge: **terminology, concepts, a hierarchical taxonomy, a
practical ontology, and typed relationships** — versioned, traceable, auditable,
lineage-tracked, explainable, governed, and extensible. Knowledge is **data, not
logic hidden in code**, and this layer is emphatically **not a diagnosis engine**
and contains **no decision support** (forbidden / V2-P6+).

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `terminology/` | Versioned terms (term, definition, source, status, relations). |
| `concepts/` | Versioned concepts related to terms + evidence + taxonomy. |
| `taxonomy/` | Hierarchical taxonomy (6 categories) with acyclicity/depth consistency checks. |
| `ontology/` | Practical ontology: entity kinds + relationship schema + executable constraints. |
| `relationships/` | Typed, versioned, endpoint-validated edges (the mandated relationship types). |
| `evidence/` | Knowledge↔evidence links (grounds knowledge in registered evidence). |
| `identity.py` | Deterministic content-addressed ids (term/concept/taxon/relation/knowledge). |
| `audit/`, `lineage/`, `registry/`, `validation/`, `reports/`, `schemas/` | Governance substrate. |
| `seed.py` | **Declarative** default knowledge (ACNS EEG terms + platform concepts) — data. |
| `service.py` | `KnowledgeService` — the governed orchestration hub. |

## Relationships (knowledge ↔ clinical graph)

`finding_describes_concept`, `interpretation_refers_concept`, `case_has_finding`,
`review_produced_finding`, `finding_supported_by_evidence`,
`knowledge_grounded_in_evidence`, `knowledge_uses_terminology`, `concept_has_term`,
`concept_in_taxon`. Each predicate declares its subject/object kinds; endpoints are
validated; relationship lineage nodes parent **both** endpoints, connecting the
knowledge graph to the clinical graph (the deliverable's "Knowledge Context").

## Guardrails

Descriptive knowledge only — no diagnostic inference, no decision support, no
treatment logic. Every artifact is versioned, audited, and lineage-tracked; the
seed is data loaded through governed methods.

## Integration & boundary (NR-8)

Imports `ml` + the sibling `backend.clinical_cases` (audit primitive); shares the
lineage tracker so concepts/relationships connect to findings/inference. Never
imports `frontend`. No FHIR/HL7/EMR.

See [`docs/V2_P4_CLINICAL_KNOWLEDGE.md`](./docs/V2_P4_CLINICAL_KNOWLEDGE.md).
