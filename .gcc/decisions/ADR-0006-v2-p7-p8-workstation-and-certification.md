# ADR-0006 — V2-P7 Clinical Workstation + V2-P8 Version 2 Certification

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V2-P7 + V2-P8
> **Builds on:** ADR-0001…ADR-0004, [ADR-0005](./ADR-0005-v2-p5-p6-intelligence-and-decision-support.md)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-5/AP-8/NR-11
> (traceability/audit), AP-6/NR-9/NR-10 (determinism/reproducibility), AP-7/NR-8
> (boundaries — `frontend` imports no domain module), AP-9/NR-5 (this record),
> NR-12 (version gate), NR-13 (scope)
> **Decision owner:** Application/Presentation + GCC (Kiro-assisted, subject to NR-7)

Captures why the V2-P7 Clinical Workstation and the V2-P8 certification are shaped
as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

After V2-P1…P6 the platform had six governed subsystems (cases, reviews, findings,
knowledge, multi-case intelligence, decision support) but users still interacted
with them piecemeal. V2-P7 unifies them into one operational environment; V2-P8
performs a **real audit** to decide whether Version 2 is genuinely complete.

## 2. Decisions

### D1 — The workstation is a presentation layer that imports nothing internal (NR-8)
`frontend/` is the strictest boundary in the architecture: it imports **no** domain
module (enforced by `tests/test_boundaries.py::test_frontend_imports_no_domain_module`).
The Clinical Workstation therefore renders a **snapshot** (a JSON document of
registered artifacts) using stdlib `json` only. It mirrors the V1
`offline_research_app` precedent (ADR-0002): the presentation layer never imports
`backend`/`ml`.

### D2 — A `scripts/` serializer is the single composition seam
`scripts/build_workstation_snapshot.py` composes the real V2 services over **one
shared `ml.lineage.LineageTracker`**, runs a small deterministic multi-case
workflow, and serializes every registered artifact (registries, reports, immutable
audit logs, the lineage graph, validation results) into the snapshot. Scripts may
import any layer; this is the sanctioned place to cross from backend to a frontend
input, exactly like `run_clinical_workflow`. The snapshot is deterministic
(DETERMINISTIC_EPOCH everywhere; sorted JSON) so it is byte-reproducible.

### D3 — The workstation is a source of *view*, never a source of *truth*
Everything displayed originates from a registered artifact; the workstation creates
no hidden state. The only state it tracks is **deterministic navigation context**
(`current_patient/case/review/...`): a transition merely records a chosen id — it
never computes or mutates an artifact. This satisfies the directive's "never create
hidden state" and "all state transitions must be deterministic".

### D4 — Ten primary nav areas; workspaces build Page view-models
Navigation owns ten areas (System Status, Cases, Reviews, Findings, Knowledge,
Intelligence, Decision Support, Audit, Lineage, Reports). Each `NavArea` carries the
context block so navigation preserves context. Each workspace renders the registered
artifacts for its domain read-only; the Audit area is a *browser* over the backend
logs (the workstation keeps no log of its own — a deliberate, documented boundary).

### D5 — Workstation validation is consistency, not recomputation
The seven checks (artifact / registry / version / audit / lineage / workflow / state
consistency) confirm the rendered view is coherent and fully traceable using the
validation/audit/lineage facts the backend already recorded. `workflow_consistency`
treats Knowledge (`concept`) and Intelligence (`analytics`) as **parallel** lineage
branches (not ancestors of a single decision node), so it checks presence against
the whole lineage graph while requiring the Patient→…→Decision Support spine to
verify. The workstation has its **own** tiny `ValidationReport` (it must not import
`ml.validation`).

### D6 — Certification is earned, mirrors the V1 package, and is honestly QUALIFIED
V2-P8 reuses the V1 certification template (8 documents) and the same evidence-driven
method. The audit is real: every claim cites a test, a verify-script criterion, or a
registered artifact. The verdict is **CERTIFIED (QUALIFIED)** — the delivered V2
workflow platform is Strong and fully verifiable, but three foundations **inherited
from V1** remain provisional (synthetic data G1; unmechanized `.gcc/` governance G2;
in-memory persistence G3). No exit criterion FAILs. Per NR-12, the **V3 Readiness
Gate is NOT GRANTED**, with measurable entry criteria E1–E8.

### D7 — Reuse, determinism, tests in top-level `tests/` (ADR-0001 D4)
The workstation reuses the view-model/section/visualization idioms from the research
app; `scripts.verify_v2_p7_p8` checks all 20 criteria; tests live in
`tests/test_clinical_workstation.py`. No new runtime dependency is introduced.

## 3. Consequences

- The required deliverable operates through a unified environment: Patient → Case →
  Review → Finding → Interpretation → Knowledge → Multi-Case Intelligence → Decision
  Support → Clinical Workstation → Audit Trail → Lineage Trail
  (`python -m scripts.verify_v2_p7_p8` → all 20 criteria PASS).
- Acyclic DAG preserved; `frontend` still imports nothing internal
  (`tests/test_boundaries.py`). V1 and V2-P1…P6 remain intact (their artifacts are
  *read* via the snapshot, never mutated). 240 tests pass.
- Version 2 is **CERTIFIED (QUALIFIED)**; V3 entry is gated on E1–E8.

## 4. Scope guard (explicitly NOT built — NR-13)

No FHIR/HL7, no EMR/hospital integration, no real-time/streaming EEG, no deployment
infrastructure, no multi-user production, no V3/V4 features, and no diagnosis/
treatment surfacing. The workstation only presents what V2 already produced and
registered.

## 5. Follow-ups / recorded debt (NR-2)

- Close V2 Gaps G1–G3 (real-EEG validation; mechanized `.gcc/` governance; durable
  checksummed persistence for the V2 subsystems) to reach unqualified CERTIFIED.
- Register the workstation snapshot itself as a checksummed artifact (G4).
