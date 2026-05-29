# LAYERED ARCHITECTURE

> **Document type:** Repository Architecture Foundation (V0-P2)
> **Status:** Authoritative
> **Owner:** Founder (Architecture Owner role)
> **Update procedure:** Governance-class change (ADR — [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md)); architecture changes require an ADR (NR-5/NR-8).
> **Realizes:** [`../ARCHITECTURAL_PRINCIPLES.md`](../ARCHITECTURAL_PRINCIPLES.md) (esp. AP-7 modularity, AP-11 governance), [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md)
> **Companion docs:** [`SYSTEM_CONTEXT.md`](./SYSTEM_CONTEXT.md), [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md), [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md), [`IMPORT_RULES.md`](./IMPORT_RULES.md)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

NeuroVision AI is organized into **seven layers**. Five are *stacked* domain/
application layers with a strict one-way dependency order; two — **Governance**
and **Context** — are **cross-cutting** and surround the stack. This layering is
the structural realization of the platform's principles, and it is designed to
remain intact from V0 through V4 (Principle **AP-1**, no rewrites).

---

## 1. The Seven Layers

| # | Layer | Directory(ies) | Role |
|---|-------|----------------|------|
| 1 | **Presentation** | `frontend/` | Clinician-facing UI; faithfully presents results + uncertainty. |
| 2 | **Application** | `backend/` | Orchestrates domain logic; exposes APIs; preserves uncertainty/provenance. |
| 3 | **ML** | `ml/` | Models + uncertainty-aware inference. |
| 4 | **DSP** | `preprocessing/` | Deterministic signal processing (leaf of the stack). |
| 5 | **Infrastructure** | `deployment/`, `monitoring/` | Packaging, deployment, observability, drift detection. |
| — | **Governance** *(cross-cutting)* | `.gcc/` | Enforces boundaries/rules; decision records; audit; drift detection (GCC). |
| — | **Context** *(cross-cutting)* | `docs/` | Durable intent, rationale, terminology (Lore Protocol). |

> Two supporting module groups participate in the stack but are not separate
> *layers*: **`datasets/`** (a data-access module feeding the ML/DSP layers) and
> **`evaluation/`** (a validation module consuming ML/Datasets/DSP). They are
> placed precisely in [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md) and
> [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md).
>
> Two cross-cutting *support* areas — **`tests/`** and **`tools/` + `scripts/`** —
> sit outside the production dependency graph (test-only / developer-only) and are
> defined in their READMEs and the import rules.

---

## 2. The Layer Stack (vertical view)

```
            ┌──────────────────────────────────────────────────────┐
   CONTEXT  │  docs/  — durable intent, rationale, terminology       │  cross-cutting
   LAYER    │          (Lore Protocol)                               │  (surrounds all)
            └──────────────────────────────────────────────────────┘
            ┌──────────────────────────────────────────────────────┐
 GOVERNANCE │  .gcc/  — boundaries, decision records, audit, drift   │  cross-cutting
   LAYER    │          (Governance & Context Control / GCC)          │  (governs all)
            └──────────────────────────────────────────────────────┘
   ┌───────────────────────────────────────────────────────────────────┐
   │  (1) PRESENTATION        frontend/        clinician UI              │
   │            │  depends on (API only)                                 │
   │            ▼                                                        │
   │  (2) APPLICATION         backend/         services / APIs           │
   │            │  depends on                                           │
   │            ▼                                                        │
   │  (3) ML                  ml/              models + uncertainty      │
   │            │  depends on                                           │
   │            ▼                                                        │
   │  (4) DSP                 preprocessing/   deterministic transforms  │ ◄── leaf
   │                                                                     │
   │   supporting: datasets/ (feeds ML, uses DSP) · evaluation/ (uses    │
   │   ML+datasets+DSP)                                                  │
   └───────────────────────────────────────────────────────────────────┘
            ┌──────────────────────────────────────────────────────┐
   INFRA    │  deployment/ (packages & deploys)                      │  wraps the stack
   LAYER    │  monitoring/ (observes & detects drift)                │  (one-way)
            └──────────────────────────────────────────────────────┘
```

**Rule of the stack:** a layer may depend only on layers **below** it; never on a
layer above. Infrastructure *wraps* the stack (deploys/observes it) without being
imported by it. Governance and Context *surround* the stack and are imported by
nobody.

---

## 3. Each Layer In Detail

### (1) Presentation Layer — `frontend/`
- **Does:** render detections/IIC and **uncertainty** for clinician review/triage.
- **Depends on:** the **Application layer via API only** — it imports **no** domain
  module (Rule **NR-8**; the canonical forbidden-import example).
- **Never:** contains DSP/ML/data/evaluation logic; never hides uncertainty (NR-4).

### (2) Application Layer — `backend/`
- **Does:** orchestrate `ml`/`evaluation`/`datasets`/`preprocessing` into use
  cases; expose APIs; **preserve uncertainty and provenance**; own the audit trail.
- **Depends on:** ML, DSP, and the supporting data/eval modules (downward only).
- **Never:** imports `frontend/`; never flattens uncertainty (NR-4) or emits
  untraceable outputs (NR-11).

### (3) ML Layer — `ml/`
- **Does:** define/train models; produce **uncertainty-aware** inference with
  provenance.
- **Depends on:** `preprocessing/` and `datasets/`.
- **Never:** imports `evaluation/` (evaluation imports ml — no cycle), `backend/`,
  or `frontend/`; never emits bare labels as clinical output (NR-4).

### (4) DSP Layer — `preprocessing/`
- **Does:** deterministic, versioned signal processing — the reproducibility leaf.
- **Depends on:** **nobody** inside the platform (third-party numerics only).
- **Never:** imports any platform module; never introduces nondeterminism (NR-9).

### (5) Infrastructure Layer — `deployment/`, `monitoring/`
- **Does:** package/deploy the platform (`deployment/`); observe behavior and
  detect drift (`monitoring/`).
- **Depends on:** tooling/configuration; references artifacts.
- **Never:** imports domain modules into itself, and is **never imported by** them.
  Domain code's only tie to monitoring is **emitting telemetry via shared contracts**.

### Governance Layer (cross-cutting) — `.gcc/`
- **Does:** mechanize boundaries/import rules, decision records, debt registry,
  version gates, drift detection (GCC; Principle **AP-11**).
- **Depends on:** read access to the whole repo + `tools/`.
- **Never:** imported by any production module; never redefines the constitution
  (it enforces what `docs/` declares).

### Context Layer (cross-cutting) — `docs/`
- **Does:** preserve durable intent, rationale, terminology (Lore Protocol); is the
  canonical source of truth for meaning and architecture.
- **Depends on:** nothing at runtime.
- **Never:** contains executable domain code.

---

## 4. Information Flow

The flow of *data/results* (left→right) is distinct from the flow of
*dependencies* (which points downward only).

```
 raw EEG
   │
   ▼
 preprocessing (DSP) ──► datasets ──► ml (inference + uncertainty)
                                         │
                                         ▼
                                   backend (preserve uncertainty + provenance,
                                            build audit trail, expose API)
                                         │
                                         ▼ (API)
                                   frontend (faithful uncertainty for clinician)

 evaluation  ◄── reads ml + datasets + preprocessing to produce patient-disjoint metrics
 monitoring  ◄── receives telemetry emitted by backend/ml at runtime (via contracts)
 .gcc        ◄── inspects all modules + records decisions (governs, not in data path)
 docs        ◄── records why all of the above is shaped this way (Lore Protocol)
```

- **Uncertainty** is created in ML and must survive untouched through Application
  to Presentation (Principle **AP-4**).
- **Provenance** is attached as early as preprocessing/inference and accumulated
  through to the audit trail (Principle **AP-5**).

## 5. Dependency Flow (the hard constraint)

Dependencies point **downward only** and the graph is **acyclic**:

```
frontend → backend → { ml, evaluation, datasets, preprocessing }
                       ml → { preprocessing, datasets }
                       datasets → preprocessing
                       evaluation → { ml, datasets, preprocessing }
                       preprocessing → (nobody)
infrastructure (deployment, monitoring): one-way, wraps the stack
governance (.gcc) & context (docs): cross-cutting, imported by nobody
```

The exact allowed/forbidden edges are enumerated in
[`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md) and
[`IMPORT_RULES.md`](./IMPORT_RULES.md). Any upward or circular dependency is an
**architecture-drift** violation (Rule **NR-8**), detected by the Governance layer.

---

## 6. Why This Layering

- **Maintainability/safety:** strict layers contain change and let each part be
  reasoned about and tested in isolation (AP-7).
- **Reproducibility:** placing deterministic DSP at the leaf means everything above
  inherits a reproducible foundation (AP-3/AP-6).
- **Trust:** uncertainty flowing top-down through dedicated layers guarantees it
  cannot be silently dropped (AP-4).
- **Governance:** making Governance/Context cross-cutting (not buried in a module)
  is what lets the platform police itself (AP-8/AP-11).

---

## 7. Future Scaling Path (V0 → V4)

The layering does not change shape across versions; layers are **populated and
hardened**:

| Version | What fills/hardens |
|---------|--------------------|
| **V0** | All layers *defined*; Governance/Context established; no runtime code. |
| **V1** | DSP, ML, Datasets, Evaluation become real (offline). |
| **V2** | Application + Presentation become real (clinical workflow + audit trail). |
| **V3** | Infrastructure matures (near-real-time + monitoring/drift). |
| **V4** | All layers hardened for hospital deployment under full governance. |

Scaling is **vertical population and hardening**, never re-layering (Principle
**AP-1**, Rule **NR-6**).

---

## 8. Relationship To Other Documents
- Conceptual map for [`SYSTEM_CONTEXT.md`](./SYSTEM_CONTEXT.md).
- Realized as concrete edges in [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md) and
  rules in [`IMPORT_RULES.md`](./IMPORT_RULES.md).
- Detailed per-module in [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md).
- Enforced by `.gcc/` ([`../../.gcc/README.md`](../../.gcc/README.md)).
