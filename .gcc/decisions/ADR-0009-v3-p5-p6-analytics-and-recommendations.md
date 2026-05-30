# ADR-0009 — V3-P5 Operational Analytics Layer + V3-P6 Operational Recommendation Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V3-P5 + V3-P6
> **Builds on:** ADR-0001…ADR-0008
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V3-P5 Operational Analytics Layer and V3-P6 Operational
Recommendation Layer are shaped as they are, so the rationale survives turnover
(NR-14).

---

## 1. Context

V3 (P1–P4) gave the platform events, time, workflows, and a structured operational
graph. It still could not understand **operational patterns, health, performance,
risk** or produce **explainable recommendations**. V3-P5 creates platform-wide
**operational intelligence** (intelligence only — no actions). V3-P6 turns that
intelligence into **explainable operational recommendations** (suggestions only).
Both must evolve the existing operational foundations — not replace event/temporal/
workflow/graph semantics, not create parallel lineage or audit systems.

## 2. Decisions

### D1 — Two new `backend` subsystems, vertical population only (AP-1)
`backend/operational_analytics` (V3-P5) and `backend/operational_recommendations`
(V3-P6) populate the Application layer. They import `ml` + sibling `backend`
subsystems; never `frontend` (enforced by `tests/test_boundaries.py`). No layer is
added or re-drawn.

### D2 — Analytics is derived intelligence; never a source of truth
Analytics is computed strictly from already-governed artifacts — events (V3-P1),
temporal intelligence (V3-P2), workflows (V3-P3), the operational graph (V3-P4) —
read through the single, deterministic `AnalyticsSourceView`. The governance "risk"
dimension fails any analytics record that is not derived from upstream sources,
mechanizing **analytics must never become a source of truth**. Six engines
(metrics, health, performance, quality, trend, risk) each emit explainable
`AnalyticsMetric`s; a composite `operational` record carries the headline signal of
each dimension. The risk engine emits **risk scores only** — never recommendations.

### D3 — No black-box recommendations; evidence- + analytics-linked (V3-P6)
Every recommendation cites `RecommendationEvidence` referencing a real upstream
artifact and links to the analytics records it reasoned over. The governance "risk"
dimension fails any recommendation that is not **both evidence-linked and
analytics-linked**, mechanizing **no black-box recommendations**. Five engines —
context (deterministic context bundle), guidance, prioritization (explainable
banded priority), optimization (suggestions), escalation (candidates) — produce
explainable outputs.

### D4 — Suggestions only; operational, never clinical (NR-13)
Recommendations are **suggestions**: nothing is executed, no queue is reordered, no
dependency is changed, and escalation produces **candidates** for human review —
never automatic escalation (the service exposes no execute/apply/escalate API). The
layer operates **exclusively on operational/workflow/system intelligence** — it is
not clinical decision support, medical advice, diagnosis, or treatment.

### D5 — No parallel lineage/audit; shared mechanisms reused (directive mandate)
Both subsystems **share** the platform's single `ml.lineage.LineageTracker` and the
shared `ImmutableAuditLog`. Analytics lineage nodes parent the event/workflow/graph/
temporal nodes they summarize; recommendation lineage nodes parent the analytics
nodes they cite — so `verify_chain` from any analytics or recommendation artifact
reaches the patient. They keep their own *registries* (for the new artifact kinds)
but never duplicate lineage/audit or wrap existing registries.

### D6 — Time stays a deterministic logical clock (NR-9/NR-10)
There is no wall-clock anywhere. Durations/latencies are logical steps; trends are
computed over the deterministically-ordered event stream split into two equal
logical halves (earlier vs later); priority banding is fixed. Identical inputs
reproduce identical analytics, recommendations, versions, and audit heads.
Timestamps were rejected as non-reproducible.

### D7 — Reuse + tests in top-level `tests/` (ADR-0001 D4)
`ml.provenance.hash_obj`, `ml.lineage`, `ml.validation.ValidationReport`, and the
shared `ImmutableAuditLog` are reused. The recommendation layer reuses the V3-P5
`AnalyticsCategory` constants (an allowed intra-`backend` import) rather than
re-declaring them. Tests live in `tests/` (`test_operational_analytics.py`,
`test_operational_recommendations.py`, `test_v3_p5_p6_e2e.py`);
`scripts/verify_v3_p5_p6.py` checks all 22 criteria.

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Review → Finding → Knowledge → Decision → Event → Timeline → Workflow → Graph →
  **Operational Analytics → Operational Risks → Operational Recommendations**
  (`python -m scripts.verify_v3_p5_p6` → all 22 criteria PASS).
- Acyclic DAG preserved; the new subsystems import `ml` + intra-`backend` only,
  never `frontend`. V2 and V3-P1…P4 remain intact (analytics/recommendations only
  *read* them — sources are never mutated). 340 tests pass (was 300, +40).

## 4. Scope guard (explicitly NOT built — NR-13)

Operational dashboards, operational workstation, realtime/autonomous execution,
auto escalation, clinical recommendations, diagnosis, treatment, FHIR/HL7/EMR
integration, and any V4 feature.

## 5. Follow-ups / recorded debt (NR-2)

- A future presentation layer can surface analytics/recommendations in the Clinical
  Workstation by extending the snapshot builder (no domain import in `frontend`).
- Durable, checksummed persistence for the analytics/recommendation registries (the
  inherited V2 Gap G3) remains the natural next increment.
