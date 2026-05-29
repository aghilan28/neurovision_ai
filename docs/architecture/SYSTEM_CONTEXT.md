# SYSTEM CONTEXT

> **Document type:** Repository Architecture Foundation (V0-P2)
> **Status:** Authoritative
> **Companion docs:** [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md), [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md), [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md), [`IMPORT_RULES.md`](./IMPORT_RULES.md)
> **Upstream:** [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md), [`../PROJECT_VISION.md`](../PROJECT_VISION.md)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document gives the **highest-level view** of NeuroVision AI: how the system
sits in its clinical context, how its subsystems relate, how those relationships
**evolve across versions**, where **future integration points** are, and how the
whole design **aligns with the Version 4 destination**. It is the "zoom out" that
the other architecture docs "zoom in" from.

---

## 1. High-Level Architecture (system context diagram)

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                          EXTERNAL CONTEXT (ICU / Hospital)                 │
  │                                                                            │
  │   EEG acquisition ──► raw cEEG ──►  [ NeuroVision AI ]  ──► clinician      │
  │   (hardware/montage)                                       (review/triage) │
  │                                                                            │
  └──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                              NeuroVision AI                                │
  │                                                                            │
  │   CONTEXT LAYER (docs/) ── records WHY everything below is shaped this way │
  │   ──────────────────────────────────────────────────────────────────────  │
  │   GOVERNANCE LAYER (.gcc/) ── enforces boundaries, decisions, audit, drift │
  │   ──────────────────────────────────────────────────────────────────────  │
  │                                                                            │
  │     ┌────────────┐   API    ┌────────────┐                                │
  │     │ PRESENTATION│ ◄──────► │ APPLICATION│                                │
  │     │  frontend/ │          │  backend/  │                                │
  │     └────────────┘          └──────┬─────┘                                │
  │                                     │ orchestrates (preserves uncertainty  │
  │                                     │ + provenance, builds audit trail)    │
  │        ┌────────────────────────────┼───────────────────────────┐         │
  │        ▼                ▼            ▼               ▼            ▼         │
  │   ┌─────────┐    ┌───────────┐  ┌─────────┐   ┌───────────┐                │
  │   │   ml/   │◄───│evaluation/│  │datasets/│   │preprocess/│ (DSP leaf)      │
  │   │  (ML)   │    │(validation│  │ (data)  │──►│ determinis│                │
  │   └────┬────┘    │ patient-  │  └────┬────┘   │ tic, leaf │                │
  │        │  uses   │ disjoint) │       │ uses   └───────────┘                │
  │        └─────────┴───────────┴───────┘  (all converge on preprocessing)    │
  │                                                                            │
  │   INFRASTRUCTURE LAYER:  deployment/ (packages & runs) · monitoring/       │
  │   (observes runtime, detects drift) ── one-way, wraps the stack            │
  │                                                                            │
  │   SUPPORT (outside prod graph):  tests/ · tools/ · scripts/                │
  └──────────────────────────────────────────────────────────────────────────┘
```

**Reading the diagram.** Data flows from EEG acquisition through the DSP/Data/ML
modules, is orchestrated by the Application layer (which preserves uncertainty and
provenance and builds the audit trail), and is presented to the clinician through
the Presentation layer over the API. The Governance and Context layers surround
everything; Infrastructure wraps the stack one-way.

---

## 2. Subsystem Relationships

| Subsystem | Relates to | Nature of relationship |
|-----------|-----------|------------------------|
| Presentation ↔ Application | `frontend` ↔ `backend` | **API only** (network); never a code import. Uncertainty + provenance cross this boundary intact. |
| Application → Domain | `backend` → `ml`/`evaluation`/`datasets`/`preprocessing` | Orchestration (downward code dependency). |
| ML → Data/DSP | `ml` → `datasets`/`preprocessing` | Consumes leakage-safe, deterministic inputs. |
| Evaluation → ML/Data/DSP | `evaluation` → `ml`/`datasets`/`preprocessing` | Grades models on patient-disjoint data (no reverse edge). |
| Data → DSP | `datasets` → `preprocessing` | Produces model-ready, patient-indexed data. |
| Infrastructure ↔ Stack | `deployment`/`monitoring` ↔ stack | One-way: deploys/observes; not imported by the stack. Domain **emits telemetry** to monitoring via contracts. |
| Governance ⟂ All | `.gcc` ⟂ everything | Cross-cutting enforcement; imported by nobody. |
| Context ⟂ All | `docs` ⟂ everything | Cross-cutting rationale/terminology; imported by nobody. |

All relationships are constrained by the [dependency graph](./DEPENDENCY_GRAPH.md)
and [import rules](./IMPORT_RULES.md); they are **acyclic** and **one-way**.

---

## 3. Version Evolution Relationships

The system context **shape is fixed**; what changes across versions is **which
subsystems are populated and active.** (See
[`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md).)

```
 V0  Context + Governance established; all modules defined, none implemented.
        docs/ ✔   .gcc/ (V0-P3) ✔   [stack defined, empty]

 V1  DSP + Data + ML + Evaluation become real (offline, patient-disjoint, UQ).
        preprocessing ✔  datasets ✔  ml ✔  evaluation ✔   [frontend/backend still empty]

 V2  Application + Presentation become real (clinical workflow + audit trail).
        backend ✔  frontend ✔   (uncertainty + provenance now reach the clinician)

 V3  Infrastructure matures (near-real-time + monitoring/drift).
        deployment ◐  monitoring ✔   (streaming reuses V1 preprocessing + UQ)

 V4  All layers hardened for hospital deployment under full governance.
        deployment ✔  monitoring ✔  .gcc audit complete   (Hospital-Ready Foundation)
```

Legend: ✔ active/mature · ◐ maturing · empty = defined-but-not-implemented.

**Key relationship invariant across versions:** once a subsystem relationship is
active (e.g. uncertainty flowing ML → backend → frontend), it is **never
weakened** in a later version (cross-version invariants,
[`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §6).

---

## 4. Future Integration Points

These are **defined-but-dormant** seams where later versions and FUTURE-scope
capabilities attach **without re-architecting** (Principle **AP-1**). Each must
preserve the dependency graph and all invariants.

| Integration point | Where it attaches | Earliest | Constraints |
|-------------------|-------------------|----------|-------------|
| **EEG acquisition / streaming source** | below `datasets/` (ingest) | V3 | Must preserve patient-disjoint semantics + determinism. |
| **New detection patterns** (e.g. burst-suppression) | within `ml/` + `evaluation/` boundaries | V2+ | Same UQ + patient-disjoint requirements; Scope F1. |
| **Site/domain adaptation** | `ml/` (+ `monitoring/` for drift) | V4 | Serves domain-shift robustness; Scope F4. |
| **Narrow multimodal context** (EEG + vitals) | `datasets/` → `ml/` | V3+ | Only if it serves in-scope detection; Scope F3. |
| **Hospital systems** (EEG/clinical IT) | `backend/` API + `deployment/` | V4 | Via API/deployment; no vendor lock-in (Scope R7). |
| **Regulatory/audit artifact export** | `.gcc/` + `docs/` | V4+ | Built on the existing audit trail; Scope F6. |
| **Federated/privacy-preserving training** | `datasets/` + `deployment/` | Post-V4 | Large governance/security implications; Scope F5. |

A new integration point is activated only via a **recorded governance decision**
(Rule **NR-5**) and must pass GCC boundary checks.

---

## 5. Version 4 Alignment

Every element of this system context is chosen so that **Version 4 (Hospital-Ready
Foundation)** is reachable by **populating and hardening** the existing structure —
never by rewriting it. The alignment:

| V4 requirement | How the V0 system context already provides for it |
|----------------|----------------------------------------------------|
| **Deployable** in a hospital | Infrastructure layer (`deployment/`) exists as a one-way wrapper from the start; API boundary isolates the frontend. |
| **Governable** | Governance layer (`.gcc/`) is cross-cutting and present from V0-P3; boundaries are machine-checkable. |
| **Auditable** end-to-end | Provenance attached from DSP/ML; audit trail owned by `backend/`; verified by `.gcc/`. |
| **Reliable** under shift/load | Domain-shift awareness in `evaluation/`; drift detection in `monitoring/`; streaming added as an extension in V3. |
| **Maintainable** for a decade | Strict layering + Lore Protocol (`docs/`) keep the system understandable and changeable without rewrites. |
| **In scope / safe** | The structure makes out-of-scope work (e.g. autonomous decisions) architecturally unnatural and governance-blocked. |

**V4 is a maturity state of *this* architecture** — not a different system, and
**not** a regulatory-clearance claim (see [`../PROJECT_VISION.md`](../PROJECT_VISION.md) §7).

---

## 6. How To Use This Document

- **Newcomers (human or AI):** read this first among the architecture docs to get
  the whole picture, then descend into
  [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md) →
  [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md) →
  [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md) →
  [`IMPORT_RULES.md`](./IMPORT_RULES.md).
- **Before adding a capability:** locate the correct subsystem/integration point
  above; confirm the version owns it; confirm it preserves the dependency graph
  and invariants; record the decision.

## 7. Relationship To Other Documents
- This is the architectural "zoom out"; the companions are the "zoom in."
- Version semantics: [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md).
- Scope of integration points: [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md).
- Enforcement of all relationships: [`../../.gcc/README.md`](../../.gcc/README.md).
