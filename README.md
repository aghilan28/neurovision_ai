---
title: NeuroVision AI
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: docker
---

# NeuroVision AI

> **A production-oriented EEG-AI platform for critical-care neurology.**
> NeuroVision AI assists clinicians in detecting and characterizing seizures and
> the **Ictal-Interictal Continuum (IIC)** in the ICU from continuous EEG (cEEG),
> with **calibrated uncertainty** on every clinically meaningful output.

| | |
|---|---|
| **Current version** | **Version 0 — Repository Foundation** |
| **Current phase** | **V0-P1 (Project Constitution Layer) + V0-P2 (Repository Architecture Foundation)** — complete |
| **Next phase** | **V0-P3 (Governance Layer)** — implement `.gcc/` mechanisms |
| **Status** | Foundation only. **No EEG processing, models, datasets, APIs, dashboards, or pipelines exist yet** — and that is by design. |
| **Optimizing for** | Survivability · maintainability · architectural integrity (never speed/convenience) |

---

## 1. What This Project Is

NeuroVision AI is a **multi-year platform**, not a model, notebook, prototype, or
competition entry. It is engineered to evolve through five deliberate versions,
culminating in a **Hospital-Ready Foundation (Version 4)**:

| Version | Name | Mission |
|---------|------|---------|
| **V0** | Repository Foundation | Build the permanent foundation everything depends on. |
| **V1** | Offline EEG Platform | Prove rigorous, reproducible, patient-disjoint, uncertainty-aware offline interpretation. |
| **V2** | Clinical Workflow Platform | Make outputs usable in a real clinical review workflow, fully traceable. |
| **V3** | Near Real-Time Platform | Detect in time to matter, without sacrificing validation integrity. |
| **V4** | Hospital-Ready Foundation | Be deployable, governable, auditable, and reliable in a hospital. |

The platform is **decision-support**: the clinician is always the decision-maker.

> New here? Read [`docs/PROJECT_VISION.md`](docs/PROJECT_VISION.md) first, then the
> [documentation map](#4-documentation-map) below.

---

## 2. Why This Project Exists (in one paragraph)

EEG-AI rarely reaches patients because of predictable failures: evaluation on
leaked (non-patient-disjoint) splits, overconfident predictions with no honest
uncertainty, irreproducible pipelines, undocumented architecture, and constant
rewrites. NeuroVision AI is structured to **close that translation gap by
construction** — treating **patient-disjoint validation**, **calibrated
uncertainty**, **deterministic/reproducible preprocessing**, and **mechanized
governance** as non-negotiable platform features rather than afterthoughts. The
full argument is in [`docs/PROJECT_VISION.md`](docs/PROJECT_VISION.md).

---

## 3. Repository Structure

The directory tree is **permanent**: it is designed to survive unchanged (in
shape) from V0 through V4. Each directory carries a `README.md` defining its
purpose, responsibilities, allowed/forbidden dependencies, version ownership, and
boundary rules.

```
neurovision_ai/
├── README.md                  ← you are here (repository entry point)
├── docs/                      Context Layer — constitution + architecture (the Lore Protocol)
│   ├── PROJECT_VISION.md
│   ├── PROJECT_OBJECTIVES.md
│   ├── PROJECT_SCOPE.md
│   ├── VERSION_EVOLUTION_MODEL.md
│   ├── ARCHITECTURAL_PRINCIPLES.md
│   ├── NON_NEGOTIABLE_RULES.md
│   ├── GLOSSARY.md
│   └── architecture/          dependency, boundary, import, layer & system-context docs
├── frontend/                  Presentation Layer (clinician-facing UI)            [V2+]
├── backend/                   Application Layer (services, APIs, orchestration)   [V2+]
├── ml/                        ML Layer (models, inference, uncertainty)           [V1+]
├── preprocessing/             DSP Layer (deterministic signal processing)         [V1+]
├── datasets/                  Data access & curation (patient-level, leakage-safe)[V1+]
├── evaluation/                Validation harness (patient-disjoint / LOSO)        [V1+]
├── deployment/                Infrastructure Layer — packaging & deployment       [V3/V4]
├── monitoring/                Infrastructure Layer — observability & drift        [V3/V4]
├── tests/                     Cross-cutting tests (may import any module)         [V0+]
├── tools/                     Developer/maintainer tooling (not imported by prod) [V0+]
├── scripts/                   Operational scripts (not imported by prod)          [V0+]
└── .gcc/                      Governance & Context Control layer                  [V0-P3]
```

**Dependency direction is one-way and acyclic** (top layers depend on lower
layers; never the reverse). The full rules are in
[`docs/architecture/IMPORT_RULES.md`](docs/architecture/IMPORT_RULES.md):

```
frontend ──(API only)──► backend ──► { ml, evaluation, datasets, preprocessing }
                                       ml ──► { preprocessing, datasets }
                                       datasets ──► preprocessing
                                       evaluation ──► { ml, datasets, preprocessing }
                                       preprocessing ──► (nobody)
```

---

## 4. Documentation Map

Read in this order for a complete understanding of project direction.

| # | Document | Purpose |
|---|----------|---------|
| 1 | [`docs/PROJECT_VISION.md`](docs/PROJECT_VISION.md) | Why the platform exists; the V4 vision; failure scenarios; philosophy. |
| 2 | [`docs/PROJECT_OBJECTIVES.md`](docs/PROJECT_OBJECTIVES.md) | Measurable objectives, success/failure metrics, acceptance criteria. |
| 3 | [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) | In / Out / Future / Rejected scope, with rationale. |
| 4 | [`docs/VERSION_EVOLUTION_MODEL.md`](docs/VERSION_EVOLUTION_MODEL.md) | The V0→V4 road; per-version criteria; why skipping is forbidden. |
| 5 | [`docs/ARCHITECTURAL_PRINCIPLES.md`](docs/ARCHITECTURAL_PRINCIPLES.md) | The 12 immutable principles (AP-1…AP-12). |
| 6 | [`docs/NON_NEGOTIABLE_RULES.md`](docs/NON_NEGOTIABLE_RULES.md) | The 15 project laws (NR-1…NR-15). |
| 7 | [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Canonical terminology (IIC, LOSO, GCC, Lore Protocol, …). |
| 8 | [`docs/architecture/`](docs/architecture/) | Dependency graph, module boundaries, import rules, layered architecture, system context. |
| 9 | [`docs/README.md`](docs/README.md) | Documentation index / how to navigate the docs. |

> **Single source of truth.** Terminology is governed by
> [`docs/GLOSSARY.md`](docs/GLOSSARY.md); architecture by
> [`docs/architecture/`](docs/architecture/); project law by
> [`docs/NON_NEGOTIABLE_RULES.md`](docs/NON_NEGOTIABLE_RULES.md).

---

## 5. Implementation Status

| Area | Status | Owning version |
|------|--------|----------------|
| Project Constitution Layer (V0-P1) | ✅ Complete | V0 |
| Repository Architecture Foundation (V0-P2) | ✅ Complete | V0 |
| Governance & Context Control (`.gcc/`, V0-P3) | ⏳ Contract defined; mechanisms pending | V0 |
| Preprocessing / Datasets / ML / Evaluation | ⛔ Not started (correct for V0) | V1 |
| Backend / Frontend (clinical workflow) | ⛔ Not started | V2 |
| Near-real-time / Monitoring | ⛔ Not started | V3 |
| Hospital deployment / full audit | ⛔ Not started | V4 |

There is **intentionally no executable code** in V0. The foundation is documents
and governed structure. See
[`docs/VERSION_EVOLUTION_MODEL.md`](docs/VERSION_EVOLUTION_MODEL.md).

---

## 6. Version Roadmap

```
[V0] Repository Foundation   ──►  [V1] Offline EEG Platform   ──►  [V2] Clinical Workflow
  constitution + structure         deterministic preprocessing       reviewable, traceable
  + governance (.gcc)              + patient-disjoint, UQ-aware       clinician workflow
        │                                                                     │
        └──────────────────────────────────────────────────────────────────┐ │
                                                                             ▼ ▼
                              [V4] Hospital-Ready Foundation  ◄── [V3] Near Real-Time Platform
                               deployable · governable ·            near-live ingestion +
                               auditable · reliable                 incremental inference
```

A version may not claim its exit criteria until **every prior version's exit
criteria are satisfied** (Rule **NR-12**, "Never skip a version").

---

## 7. How To Begin

### For new human contributors
1. Read the documentation map (§4) **top to bottom** — start with the vision.
2. Internalize the **12 principles** and **15 rules**; they are not optional.
3. Before any work, confirm it is **in scope**
   ([`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md)) and within the **current
   version's** objectives.
4. Find the relevant module's `README.md` and respect its boundaries and
   [import rules](docs/architecture/IMPORT_RULES.md).
5. Record consequential decisions (Rule **NR-5**) and any debt (Rule **NR-2**).

### For AI engineering agents
This repository is built to be **self-explanatory without the original research
corpus** (the Lore Protocol). Before acting:
1. Load the **constitution**: vision → objectives → scope → version model →
   principles → rules → glossary.
2. Load the **architecture**: [`docs/architecture/`](docs/architecture/) — treat
   the dependency graph and import rules as **hard constraints**.
3. Confirm the **current version/phase** (§ top of this file) and do not
   implement capability owned by a later version (Rule **NR-12**, **NR-13**).
4. Never introduce a forbidden import or weaken a cross-version invariant
   (Rules **NR-8**, **NR-3**, **NR-4**, **NR-9**).
5. All generated code is subject to human review (Rule **NR-7**).

### Golden rules (the short version)
- **Patient-disjoint or it didn't happen.** (NR-3)
- **No clinical output without calibrated uncertainty.** (NR-4)
- **Deterministic, reproducible, traceable.** (NR-9, NR-10, NR-11)
- **Respect the boundaries; never rewrite the architecture.** (NR-8, NR-6)
- **Record the why; stay in scope; never skip a version.** (NR-5, NR-13, NR-12)

---

## 8. Governance & Contributions

NeuroVision AI is governed **by construction**. The Governance & Context Control
layer ([`.gcc/`](.gcc/), formalized in V0-P3) mechanizes the boundaries and
decision records described throughout the docs. Changes to constitution or
architecture documents are **governance events** requiring a recorded, reviewed
decision (Rule **NR-5**).

---

## 9. License & Disclaimer

- **Clinical disclaimer.** NeuroVision AI is decision-support software intended to
  assist qualified clinicians; it does not provide medical advice, diagnosis, or
  treatment and does not replace clinical judgment. "Hospital-Ready (V4)" denotes
  an engineering/governance maturity state, **not** a regulatory clearance claim.
- **License.** To be established as a governance decision before any code is
  introduced (V1).

---

*This README is the repository entry point. It summarizes; the documents in
[`docs/`](docs/) govern. Where this file and a `docs/` document disagree, the
`docs/` document is authoritative and the discrepancy is a consistency defect to
fix.*
