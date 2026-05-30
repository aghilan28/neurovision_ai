# V2-P3 — Findings & Interpretation Layer (design & contracts)

> **Phase:** V2-P3 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0004`](../../../.gcc/decisions/ADR-0004-v2-p3-p4-findings-and-knowledge.md)

---

## 1. What a Finding is (and is not)

A **Finding** is a *structured clinical observation linked to evidence*. It is
**not** a prediction, probability, diagnosis, or recommendation. `FindingRecord`
carries a descriptive `observation` + `category` + optional `region` — and no
field that could encode disease inference or a course of action.

## 2. Identity

Own minting authority (`clinical_cases.identity` is left unchanged, honouring "no
redesign"). Ids are `"{kind}+{hash16}"`: `finding` (derived from a review),
`evidence` and `interpretation` (derived from a finding). Deterministic,
collision-resistant, versioned, traceable.

## 3. Mandatory evidence

`create_finding` requires ≥ 1 evidence spec; `FindingRegistry.register` rejects a
record with no evidence. Evidence links reference registered V1/V2 artifacts
(inference/calibration/conformal/coverage/risk outputs, checksummed artifacts,
reports, review actions). `evidence_confidence` is a *recorded* value, never
computed by this layer.

## 4. Interpretation kept separate

`FindingInterpretation` is its own entity (own id, version, lineage, audit trail).
The finding stores interpretation *ids* only. An interpretation's
`supporting_evidence` must be a subset of the finding's evidence (validated). Its
`confidence_level` is qualitative (low/moderate/high), never a probability.

## 5. Lifecycle

CREATED → DRAFT → UNDER_REVIEW → CONFIRMED → REVISED → SUPERSEDED → CLOSED →
ARCHIVED, with governed send-back/revise/supersede edges; ARCHIVED is terminal.
Forbidden transitions raise.

## 6. Versioning, audit, lineage

Versions chain (`hash(state_signature, previous)`) — unique per mutation. The audit
log is the shared immutable hash-chained log (bound to `FindingAuditRecord`).
Lineage: evidence nodes parent the source (inference) node; the finding node parents
the review node + its evidence nodes; interpretation nodes parent the finding head.
A single `verify_chain(finding.lineage_id)` proves complete upstream traceability.

## 7. Validation (7 checks)

evidence · interpretation · audit · lineage · registry · version · lifecycle
integrity. Reports: summary, audit, lineage, validation, evidence, interpretation.
