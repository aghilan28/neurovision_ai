# ADR-0005 — V2-P5 Multi-Case Intelligence Layer + V2-P6 Decision Support Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V2-P5 + V2-P6
> **Builds on:** ADR-0001, ADR-0002, ADR-0003, [ADR-0004](./ADR-0004-v2-p3-p4-findings-and-knowledge.md)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-4/NR-4 (uncertainty preserved), AP-5/AP-8/NR-11
> (traceability/audit), AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-6 (reuse),
> NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V2-P5 Multi-Case Intelligence Layer and V2-P6 Decision Support
Layer are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

V2-P1..P4 gave the platform Cases/Reviews/Findings/Interpretations/Knowledge over
V1 intelligence. Two capabilities were still missing: (a) understanding
*collections* of cases (cohort/population intelligence), and (b) structured,
explainable *decision support* for reviewers. V2-P5 adds **intelligence
generation** (never prediction); V2-P6 adds **decision support** (never diagnosis,
treatment, or autonomy). Both read existing truth and never mutate it.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/multi_case_intelligence` (V2-P5) and `backend/decision_support` (V2-P6)
populate the existing Application layer. They import `ml` + sibling `backend`
subsystems only, never `frontend` (enforced by `tests/test_boundaries.py`). No
layer is added or re-drawn.

### D2 — Own identity authorities; `clinical_cases` left untouched; `decision` stays blocked
Following the ADR-0004 D1 precedent, each new subsystem mints through its **own**
authority emitting the same `"{kind}+{hash16}"` format. V2-P5 kinds:
`cohort|analytics|trend|quality|intel_report`. V2-P6 kinds:
`decision_context|evidence_bundle|risk_context|prioritization|guidance|
decision_support|decision_report`. The bare `decision` kind that
`clinical_cases.identity` reserves and **blocks** is deliberately *not* minted —
V2-P6 produces decision *support* artifacts, never an autonomous `decision`.

### D3 — Logical id = the question; version = the answer (content-addressed, idempotent)
An artifact's logical id derives from its *definition/scope* (a cohort's criteria,
an analytics scope, a case id); its version is `hash(state_signature)`. Re-running
the same definition over evolved data yields the *same id* with a *new version*
(auditable), and re-running over identical data is idempotent. No wall-clock, no
randomness (AP-3/AP-6, NR-9/NR-10).

### D4 — One shared lineage graph; intelligence/decision nodes parent their sources
Both services share the platform's single `ml.lineage.LineageTracker`. Cohort/
analytics/trend/quality nodes parent the case/review/finding nodes; a decision
context parents case/review/finding/interpretation nodes, and evidence/risk/
prioritization/guidance/record nodes parent the context. A single `verify_chain`
from any V2-P5/P6 node therefore spans back to the patient roots, reusing — never
disturbing — V1/V2-P1..P4 lineage.

### D5 — Uncertainty is read, never recomputed (AP-4/NR-4)
The decision layer derives its risk components from the **recorded**
`evidence_confidence` carried on findings per `evidence_type` (inference/coverage/
calibration/…). It never re-runs or invents a model score; the V1 calibrated
uncertainty simply flows through.

### D6 — Governance by construction: a gate before every registry admission
Every artifact passes a governance gate (Architecture/Quality/Context/Risk) before
it is admitted to its registry, audited (immutable hash-chained log, reused from
`clinical_cases.audit`), and lineage-tracked. No artifact exists outside its
registry (AP-8/AP-11, NR-11). A `source_immutability` check compares a population
digest to a baseline to prove source truth was untouched.

### D7 — Explainability + mechanical scope enforcement (the defining V2-P6 guarantee)
Prioritization is a fixed weighted sum whose factor contributions sum exactly to
the score; risk is the mean of named components each with a textual basis; guidance
is generated from process-only templates. A `DecisionScopeGuard` scans every
human-readable field for a clinical-directive lexicon (diagnosis/treat/treatment/
therapy/prescribe/medication/dose/…); the gate's risk validation and the
validator's `decision_scope_integrity` both fail on any match, so **no
recommendation can exceed decision-support scope**. The ambiguous word "order" is
excluded to avoid false positives.

### D8 — Reuse the shared primitives (NR-6); tests in top-level `tests/` (ADR-0001 D4)
`ml.provenance.hash_obj`, `ml.lineage`, `ml.validation.ValidationReport`, and the
`ImmutableAuditLog` are reused, not reimplemented. Tests live in `tests/`
(`test_multi_case_intelligence.py`, `test_decision_support.py`,
`test_v2_p5_p6_e2e.py`); `scripts/verify_v2_p5_p6.py` checks all 20 criteria.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Interpretation → Knowledge → Cohort Intelligence → Evidence
  Context → Decision Support → Guidance → Audit Trail → Lineage Trail
  (`python -m scripts.verify_v2_p5_p6` → all 20 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend` (`tests/test_boundaries.py`). V1 and V2-P1..P4 remain intact
  (their nodes are referenced, never mutated). 217 tests pass.

## 4. Scope guard (explicitly NOT built — NR-13)

Diagnosis engines, treatment/medication recommendations, clinical orders,
autonomous decision-making, prediction, clinical deployment, FHIR/HL7, EMR
integration, real-time systems, and any V3/V4 feature. The `decision` identity kind
stays blocked; V2-P6 emits decision *support* only.

## 5. Follow-ups / recorded debt (NR-2)

- The clinical/intelligence/decision subsystems persist in-memory; durable,
  checksummed on-disk persistence (the V1 artifact-store pattern) remains the
  natural next increment.
- Decision-context "population context" currently embeds a finding-category
  frequency slice; richer cohort-relative context is a future extension.
