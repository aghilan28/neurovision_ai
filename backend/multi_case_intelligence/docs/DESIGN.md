# Multi-Case Intelligence Layer — Design (V2-P5)

## 1. Goal
Understand *collections* of clinical cases and emit governed intelligence
artifacts (cohorts, population analytics, trends, quality analytics) **without
altering source truth**. Intelligence generation, never prediction or diagnosis.

## 2. Layered position
This is a subsystem of the Application Layer (`backend/`). It reads upstream
clinical truth (V2 cases/reviews/findings/interpretations/knowledge and V1
uncertainty signals) and produces derived intelligence. It is consumed by the
Decision Support Layer (V2-P6); it never imports it (one-way).

## 3. Determinism model (AP-3, AP-6; NR-9, NR-10)
- **Canonical serialization** (`schemas/determinism.py`): key-sorted, whitespace-
  free JSON with floats quantized to 9 decimals; sets sorted; dataclasses/enums
  canonicalized. Semantically-equal values serialize byte-identically.
- **Content addressing**: `content_hash` = SHA-256 of canonical JSON;
  `deterministic_id(prefix, *parts)` mints ids from content (no UUIDs).
- **Logical clocks**: audit ordering uses a monotonically increasing sequence
  number, never the wall clock. There is no `random`/`uuid`/`datetime` anywhere
  in the production code.

Consequence: any artifact is exactly reproducible from pinned inputs.

## 4. Identity vs. version (artifact semantics)
- An artifact's **logical id** is derived from its *definition/scope* (the
  question): a cohort's id from `(member_kind, criteria)`; analytics/trend/quality
  ids from `scope`.
- Its **content hash** reflects the *result* (the answer).
- Re-running the same definition over changed data yields the **same id** with a
  **new content hash**, which the registry admits as the **next version**
  (auditing a `VERSION` event). Re-running over identical data is idempotent.

## 5. Data flow
```
SourcePopulation (immutable)
   │  read-only
   ▼
CohortBuilder ─► Cohort
AnalyticsEngine ─► PopulationAnalytics      (uses statistics/functions)
TrendAnalyzer ─► Trend                       (ordinal buckets from case.ordinal)
QualityAnalyzer ─► QualityReport
   │
   ▼
GovernanceGate.evaluate(artifact, parents)   (architecture/quality/context/risk)
   │ pass
   ▼
IntelligenceRegistry.register ──► assigns version
   ├─► IntelligenceAuditLog.record (CREATE/VERSION + REGISTER) — hash-chained
   └─► IntelligenceLineageTracker.register (parents -> transitive roots)
   ▼
ReportBuilder ─► IntelligenceReport (references only)
IntelligenceValidator.validate ─► ValidationReport
```

## 6. Lineage
The service seeds the lineage tracker with the source provenance chain
(Patient → Case → Review → Finding → Interpretation/Evidence; Knowledge is a
parentless root because it is general clinical truth). Intelligence artifacts
declare their parents; roots are resolved transitively. A cohort of findings thus
traces to patients; population-scope analytics declare the patient set as parents.

## 7. Source immutability
`SourcePopulation` is frozen and exposes an `integrity_digest()` (per-kind content
hash). The service captures a baseline at construction; `IntelligenceValidator`
compares the live digest to the baseline to **prove** no source artifact was
mutated.

## 8. Governance gate (every workflow)
`GovernanceGate` runs four checks before any artifact is registered:
- **architecture_validation** — the artifact is an intelligence-producible kind.
- **quality_validation** — structural invariants (distribution totals, non-negative
  counts, sorted/unique cohort members, version ≥ 1).
- **context_validation** — the artifact has lineage parents (traceable).
- **risk_validation** — derived ratios lie in `[0, 1]`.

## 9. What this layer deliberately does NOT do
No prediction, diagnosis, treatment, or autonomous decisions; no FHIR/HL7/EMR; no
real-time; no V3/V4 capability. It only summarizes existing truth.
