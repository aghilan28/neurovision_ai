# ADR-0010 — V3-P7 Operational Intelligence Workstation + V3-P8 Version 3 Certification

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V3-P7 + V3-P8
> **Builds on:** ADR-0001…ADR-0009
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries — `frontend ↛ domain`), AP-9/NR-5 (this record), AP-11/NR-12 (certification gate), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V3-P7 Operational Intelligence Workstation and the V3-P8 Version 3
certification are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

V3 (P1–P6) gave the platform operational understanding: events, timelines,
workflows, a graph, derived analytics, and explainable recommendations. But users
still interacted with **isolated subsystems**, and the version had not been
**audited for completion**. V3-P7 unifies the six subsystems into one operational
environment; V3-P8 performs a real certification audit. Both must **expose and
certify** the existing intelligence — not reinvent it, not replace event/temporal/
workflow/graph/analytics/recommendation semantics, and not create parallel audit or
lineage systems.

## 2. Decisions

### D1 — The workstation is a `frontend` presentation layer (AP-7/NR-8)
`frontend/operational_workstation` is the first unified **operational** interface.
Per the platform's strictest boundary, `frontend` imports **no** domain module
(enforced by `tests/test_boundaries.py`). It is presentation, navigation,
visualization, and investigation — **not** a source of truth, and **not** a
workflow/analytics/recommendation engine. The only state it holds is deterministic
navigation context.

### D2 — One snapshot seam, mirroring the V2 Clinical Workstation (AP-1)
The single seam between backend and frontend is
`scripts/build_operational_workstation_snapshot.py` (scripts may import any layer).
It composes the real V3 services over **one shared lineage tracker**, drives a small
deterministic multi-case workflow, and serializes every *registered artifact*
(registries, reports, immutable audit logs, the lineage graph, validation results)
into a single deterministic JSON snapshot (`sort_keys=True`, no wall-clock). The
workstation reads it with stdlib `json` only. This re-uses the exact pattern proven
by `build_workstation_snapshot` (V2-P7) — populate, do not re-layer.

### D3 — Ten areas, ten visualization families, six consistency checks
Navigation exposes the ten mandated areas (System Health, Events, Timelines,
Workflows, Graph, Analytics, Recommendations, Audit, Lineage, Reports). The
visualization layer provides the ten mandated chart families as plain JSON-able
specs (no recomputation). `validate_state` runs six **presentation-consistency**
checks — registry / audit / lineage / visualization / report / state — which read
the validation/audit/lineage results the backend already recorded; they do not
recompute domain truth. A unified audit browser and a lineage explorer surface
every subsystem's immutable log and the Patient→…→Recommendation chain.

### D4 — Recommendations remain operational suggestions, surfaced as such
The Recommendations workspace shows guidance, priorities, optimization suggestions,
and escalation **candidates**, each with its evidence and analytics links, and
states explicitly that these are operational suggestions only — never clinical
decision support, diagnosis, or treatment, and never executed or auto-escalated.

### D5 — Deterministic static HTML (no JavaScript)
The renderer emits a single self-contained HTML page (inline CSS + inline SVG,
CSS-only tabs, no JavaScript, no external assets), byte-deterministic for a given
view-model. This keeps the unified environment fully offline and reproducible (the
view-model and HTML are pure functions of the snapshot).

### D6 — Certification is earned, by a real audit (AP-8/AP-11/NR-12)
V3-P8 does not auto-certify. `docs/certification/v3/` holds the eight mandated
documents (standard, audit framework, readiness assessment, gap analysis, risk
review, exit criteria, completion report, V4 readiness gate). The verdict is
**CERTIFIED (QUALIFIED)** — every delivered-scope exit criterion PASSes, but three
**inherited** foundational dependencies remain provisional and disclosed: synthetic
data (G1/R1), unmechanized governance (G2/R3), and in-memory persistence (G3/R4).
A QUALIFIED verdict is an honest outcome, not a soft pass; V4 entry is **NOT
GRANTED** until E1–E8 of the V4 Readiness Gate are met.

### D7 — `scripts/verify_v3_p7_p8.py` makes the 21 criteria objective
A reproducible script checks all 21 final-validation criteria (workspaces,
visualization contracts, state, validation, the five certification documents,
governance + quality gates, V3 lineage intact, V4 criteria measurable) and exits
non-zero on any failure.

## 3. Consequences

- The required deliverable operates through one unified operational environment:
  Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
  Workflow → Graph → Analytics → Recommendations → **Operational Workstation** →
  Audit Trail → Lineage Trail (`verify_v3_p7_p8` → all 21 criteria PASS).
- Acyclic DAG preserved; `frontend/operational_workstation` imports no domain
  module. V3-P1…P6 remain intact (the workstation only *reads* registered
  artifacts; the snapshot builder mutates nothing). 363 tests pass (was 340, +23).
- Version 3 is certified **CERTIFIED (QUALIFIED)** with a measurable V4 entry gate.

## 4. Scope guard (explicitly NOT built — NR-13)

Real-time intelligence, autonomous agents, multi-site federation, distributed
intelligence, streaming EEG, FHIR/HL7/EMR integration, interactive/server UI, and
any V4 feature. The workstation creates no operational logic and no source of truth.

## 5. Follow-ups / recorded debt (NR-2)

- Close inherited Gaps G1–G3 (real-EEG validation, mechanized `.gcc/` gate in CI,
  durable checksummed persistence) to re-issue V3 as unqualified CERTIFIED.
- Register the snapshot with a sha256 manifest verified on load (G4).
