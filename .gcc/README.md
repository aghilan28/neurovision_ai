# `.gcc/` — Governance & Context Control (GCC) Layer + AI Operating System

> **Layer:** Governance Layer (cross-cutting over all other layers)
> **Directory README type:** Repository Architecture Foundation (V0-P2) **+** AI Operating System entry point (V0-P4)
> **Status:** Boundary contract defined (V0-P2); governance framework authored (V0-P3); **operating-system artifacts established (V0-P4 — this phase).**
> **Owner:** Founder
> **Update procedure:** This README is updated when OS files are added/renamed (Documentation change). Policy changes are governance-class (ADR).
> **Governing docs:** AP-1/AP-7/AP-8/AP-9/AP-11 and **all** of [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md); the framework in [`../docs/governance/`](../docs/governance/)

**GCC = Governance & Context Control.** This layer makes governance **mechanical
instead of aspirational** (Principle **AP-11**) and serves as the project's
**AI-native operating system**: the place where a human or AI agent recovers
context, finds current state, and resumes development safely — even after months
of dormancy.

This directory plays **two complementary roles**:
1. **Boundary contract (V0-P2):** GCC is a cross-cutting governance layer, imported
   by nobody, that encodes boundaries/import rules/decision records in a
   machine-checkable form (see §A below — *unchanged from V0-P2*).
2. **Operating system (V0-P4):** GCC holds the living **state, context, registries,
   protocols, templates, and checklists** that let development survive across years
   and across AI-agent turnover (see §B below).

---

## §A · Boundary Contract (V0-P2 — authoritative, unchanged)

### Purpose
Mechanize the constitution: enforce module boundaries and import rules, manage
**decision records**, maintain audit trails, and operate the **Lore Protocol** so
the repository's intent survives team and AI-agent turnover.

### Responsibilities
- **Boundary & import enforcement:** encode the rules in
  [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)
  and [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)
  as checks that **fail the build** on violation (AP-7, NR-8).
- **Decision records:** store consequential, versioned, dated decisions with
  rationale and alternatives (AP-9, NR-5).
- **Drift detection:** detect divergence of implementation from documented
  architecture (architecture drift) and loss of rationale (context drift).
- **Technical-debt registry:** record debt with risk + repayment plan; enforce the
  per-version debt budget (NR-2).
- **Version gates:** record satisfaction of each version's exit criteria and
  enforce the no-skip rule (NR-12).
- **Lore Protocol:** maintain the durable context that keeps the repository
  self-explanatory (NR-14).

### Allowed dependencies
- ✅ Read access to **all** documents and modules (it inspects the whole repo).
- ✅ Tooling utilities from `tools/` and pinned third-party check/CI libraries.

### Forbidden dependencies
- ❌ Being imported **by** any production module — governance observes and
  constrains the platform; it is not part of the application's runtime graph (NR-8).
- ❌ Containing domain logic (DSP/ML/data/serving) — that belongs in the domain
  modules.

### Version ownership
- **Owned by V0; operated continuously V0 → V4.** Contract defined in **V0-P2**;
  governance framework in **V0-P3**; operating system in **V0-P4**.

### Boundary rules
- GCC is **cross-cutting**: it governs every layer but is **not imported by** any
  of them (see [`../docs/architecture/LAYERED_ARCHITECTURE.md`](../docs/architecture/LAYERED_ARCHITECTURE.md)).
- GCC is **authoritative for enforcement**, but the **constitution documents in
  `docs/` remain the source of truth**; GCC mechanizes them, it does not redefine
  them. A conflict between a GCC check and a `docs/` rule is a defect to reconcile,
  with the `docs/` rule governing intent.
- Changes to governance mechanisms are themselves **governance events** requiring a
  recorded decision (NR-5).

> **Why this directory is hidden (`.gcc`):** the leading dot marks GCC as
> infrastructure/governance, distinct from product modules — a constant,
> cross-cutting guardian, not a feature module.

---

## §B · AI Operating System (V0-P4)

The operating system is the set of living documents below. They are **Tier 3**
(live state) in the documentation hierarchy
([`../docs/governance/Documentation_Governance.md`](../docs/governance/Documentation_Governance.md))
and are **kept current by whoever is actively working** (human or AI), under
Founder ownership.

### B.1 Entry point & master memory
| File | Purpose | Update cadence |
|------|---------|----------------|
| [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md) | Master memory — the whole project in minutes; the AI entry point. | On any change to identity/architecture/priorities. |

### B.2 State files (where are we?)
| File | Purpose | Update cadence |
|------|---------|----------------|
| [`CURRENT_STATE.md`](./CURRENT_STATE.md) | What is done now; gaps; repository status. | Continuously / end of every work session. |
| [`NEXT_STATE.md`](./NEXT_STATE.md) | Immediate objectives, upcoming work, blockers, transition criteria. | When priorities change. |
| [`VERSION_STATUS.md`](./VERSION_STATUS.md) | Per-version status, completion %, readiness, exit criteria. | At each phase/version gate. |
| [`ROADMAP_STATUS.md`](./ROADMAP_STATUS.md) | Programs → workstreams → epics → phases; critical path. | When the plan changes. |

### B.3 Live registers (what is tracked?)
| File | Purpose | Update cadence |
|------|---------|----------------|
| [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md) | Live risk register (per [`../docs/governance/Risk_Governance.md`](../docs/governance/Risk_Governance.md)). | On risk change; reviewed by cadence. |
| [`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md) | Open assumptions + evidence + verification plans. | When assumptions are made/verified. |
| [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md) | Master ADR index (per [`../docs/governance/Decision_Governance.md`](../docs/governance/Decision_Governance.md)). | On every ADR. |
| [`DEPENDENCY_REGISTRY.md`](./DEPENDENCY_REGISTRY.md) | Module/version/external/tooling/future dependencies. | On any dependency change. |

### B.4 Knowledge & context protocols (how to understand & resume?)
| File | Purpose |
|------|---------|
| [`KNOWLEDGE_GRAPH.md`](./KNOWLEDGE_GRAPH.md) | Visual graph linking objectives ↔ architecture ↔ versions ↔ risks ↔ governance ↔ AI. |
| [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md) | What Lore is; how context/decisions/learnings/postmortems are captured. |
| [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) | Deterministic sequence to reconstruct full context. |
| [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md) | Formal procedure for a new AI agent to become productive without asking the founder. |

### B.5 Workflow
| File | Purpose |
|------|---------|
| [`BRANCH_WORKFLOW.md`](./BRANCH_WORKFLOW.md) | Branch types, merge/lore/governance/review requirements. |
| [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md) | What/when/how changes are logged and traced. |

### B.6 Reusable artifacts
| Directory | Purpose |
|-----------|---------|
| [`TEMPLATES/`](./TEMPLATES/) | ADR, RFC, risk, change-record, assumption, postmortem, AI-prompt, commit-message, version-gate templates. |
| [`CHECKLISTS/`](./CHECKLISTS/) | Architecture-change, review, AI-review, release, onboarding, context-recovery, version-gate checklists. |

---

## §C · How To Use This Operating System

**A new AI agent (or a returning founder) MUST start here:**
1. Read [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md).
2. Run [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) (deterministic
   read order) and, for agents, [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md).
3. Check [`CURRENT_STATE.md`](./CURRENT_STATE.md) and [`NEXT_STATE.md`](./NEXT_STATE.md).
4. Obey the constitution (AP-1…AP-12, NR-1…NR-15) and the framework in
   [`../docs/governance/`](../docs/governance/).
5. Leave a trace (Lore + changelog) and **never self-approve** (NR-7).

> **Single source of truth:** policy lives in `docs/` (constitution, architecture,
> governance); **live state lives here** (`.gcc/`). Where they appear to conflict,
> `docs/` governs intent and the conflict is a defect to fix.
