# V2-P5 — Multi-Case Intelligence Layer

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0005](../../../.gcc/decisions/ADR-0005-v2-p5-p6-intelligence-and-decision-support.md)

A system that understands *collections* of cases. It generates **intelligence**
— cohorts, population analytics, trends, quality analytics, and summary reports —
over the populations of V2 cases, reviews, findings, interpretations, and
knowledge, **without ever altering individual case truth**. The purpose is
intelligence generation, not prediction and not diagnosis.

## What it produces
| Artifact | Module | Description |
|----------|--------|-------------|
| `Cohort` | `cohorts/` | A versioned set membership over case/review/finding/interpretation/concept populations, selected by serializable criteria. |
| `PopulationAnalytics` | `analytics/`, `statistics/` | Counts, distributions, coverage, variability, frequency, confidence — per subject kind. |
| `Trend` | `trends/` | Series over a deterministic ordinal dimension (lifecycle-stage order; per-patient case load) — never a wall-clock. |
| `QualityReport` | `quality/` | Review/finding quality, interpretation coverage, evidence richness, knowledge linkage, referential integrity. |
| `IntelligenceReport` | `reports/` | A population summary rolling up the above (references only). |

## Guarantees (how)
- **Deterministic / reproducible** — content-addressed ids (`{kind}+{hash16}` via
  `ml.provenance.hash_obj`); no wall-clock, no randomness. The artifact's *logical
  id* derives from the *definition/scope* (the question) while the *version*
  (`hash(state)`) reflects the *result*, so re-computing over evolved data yields a
  new version of the same artifact (idempotent on identical data).
- **Governed** — every artifact passes the `GovernanceGate`
  (architecture/quality/context/risk) before admission.
- **Auditable** — one shared, hash-chained `ImmutableAuditLog` (reused from
  `clinical_cases.audit`); every creation/version/registration is an immutable event.
- **Traceable** — each artifact records a node in the platform's shared
  `ml.lineage.LineageTracker`, parented by its source nodes, so a single
  `verify_chain` spans back to the patient roots.
- **Registered** — no artifact exists outside `IntelligenceRegistry`.
- **Source-immutable** — `PopulationView.integrity_digest()` is compared to a
  baseline by the `source_immutability` check, proving source truth was untouched.

## Integration boundary
Reads the *real* V2 aggregates through `PopulationView`/`PopulationBuilder`
(Cases, Reviews, Findings + Interpretations, Knowledge concepts/terms). The V1
calibrated uncertainty flows in as the **recorded** `evidence_confidence` on
findings (read, never recomputed — AP-4/NR-4). Shares the single platform lineage
tracker (`MultiCaseIntelligenceService(lineage_tracker=case_service.lineage)`).

## Scope guard (NOT built — NR-13)
No diagnosis, no prediction, no decision support (that is V2-P6), no autonomy, no
FHIR/HL7/EMR, no real-time. Intelligence only summarizes existing truth.
