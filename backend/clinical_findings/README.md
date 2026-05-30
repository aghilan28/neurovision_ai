# `backend/clinical_findings/` — Findings & Interpretation Layer (V2-P3)

> **Layer:** Application (`backend/`) · **Status:** Implemented (V2-P3).
> **Decision record:** [`../../.gcc/decisions/ADR-0004`](../../.gcc/decisions/ADR-0004-v2-p3-p4-findings-and-knowledge.md)
> **Governing docs:** AP-4/NR-4 (evidence/uncertainty preserved), AP-5/AP-8/NR-11
> (traceability/audit), AP-6/NR-10 (reproducibility), AP-7/NR-8 (boundaries)

Introduces the **Finding** as a first-class platform object: a *structured clinical
observation linked to evidence* — **never** a prediction, probability, diagnosis, or
recommendation. Findings are permanent, versioned, traceable, auditable, lineage-
tracked, review/case/evidence-linked, recoverable, governed records.

    Patient → Case → Study → Review → Evidence → Finding → Interpretation

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `identity/` | Deterministic finding/evidence/interpretation ids (own authority; `clinical_cases` left untouched). |
| `models/` | Domain entities (FindingIdentity, FindingRecord, FindingMetadata, FindingEvidence, FindingInterpretation, FindingVersion, audit/lineage/registry records, Finding). |
| `schemas/` | Per-entity contracts (Schema · Version · Validation/Version/Audit/Lineage rules). |
| `lifecycle/` | 8-state machine (CREATED→DRAFT→UNDER_REVIEW→CONFIRMED→REVISED→SUPERSEDED→CLOSED→ARCHIVED). |
| `evidence/` | Builds typed, versioned evidence links to registered V1/V2 artifacts. |
| `interpretation/` | Builds **separate** interpretation entities (never merged into the finding). |
| `audit/` | Immutable, hash-chained, tamper-evident audit log (shared primitive). |
| `lineage/` | Finding/evidence/interpretation lineage on `ml.lineage` (shared tracker). |
| `registry/` | The finding registry — no finding outside it; **rejects no-evidence findings**. |
| `validation/` | 7 integrity checks (evidence/interpretation/audit/lineage/registry/version/lifecycle). |
| `reports/` | Summary/audit/lineage/validation/evidence/interpretation reports. |
| `service.py` | `FindingService` — the governed orchestration hub. |

## Hard guardrails (the directive's limits)

- **A finding never exists without evidence** — `create_finding` requires ≥ 1
  evidence spec, and the registry rejects a record with no evidence.
- **Interpretations are separate** — the finding stores interpretation *ids*; the
  interpretation content lives in its own entity with its own version/lineage.
- **No diagnosis / recommendation / decision** — `FindingRecord` is descriptive
  only; evidence confidence is *recorded*, never computed.

## Integration & boundary (NR-8)

Imports `ml` + the sibling `backend.clinical_cases` (for id-format validation + the
audit primitive); shares the lineage tracker with the case/review/inference graphs,
so a finding's chain reaches Patient → Case → Study → Review → Inference → Evidence →
Finding → Interpretation. Never imports `frontend`. No FHIR/HL7/EMR.

See [`docs/V2_P3_CLINICAL_FINDINGS.md`](./docs/V2_P3_CLINICAL_FINDINGS.md).
