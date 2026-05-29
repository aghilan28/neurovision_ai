# `docs/` — Context Layer & Documentation Index

> **Layer:** Context Layer (operates under the **Lore Protocol**)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Parent entry point:** [`../README.md`](../README.md)

This directory is the **Context Layer** of NeuroVision AI. It holds the project
**constitution** and **architecture** documentation: the durable record of *why*
the project exists, *what* it builds, *what it never builds*, and *how* it is
structured. Under the **Lore Protocol** (see [`GLOSSARY.md`](./GLOSSARY.md)),
this directory exists so the repository remains **self-explanatory without the
original research corpus**.

---

## Purpose
Preserve and present durable project intent, rationale, terminology, and
architecture so that any future human or AI agent can reconstruct full project
direction from the repository alone.

## Responsibilities
- House the **Project Constitution Layer** (V0-P1) documents.
- House the **architecture** documents (V0-P2) under [`architecture/`](./architecture/).
- Serve as the **canonical terminology source** ([`GLOSSARY.md`](./GLOSSARY.md)).
- Record cross-cutting project knowledge that does not belong to a single module.

## Allowed dependencies
- None at runtime — documentation has no code dependencies.
- May **reference** any other document or module README via links.

## Forbidden dependencies
- Must not contain executable application/ML/DSP code.
- Must not duplicate or contradict the canonical definitions it owns; on conflict,
  the document here governs and the discrepancy is a defect to fix.

## Future responsibilities
- V1+: preprocessing specs, model cards, evaluation protocols (linked from modules).
- V2+: API contracts and audit-trail specifications (authored with `backend/`).
- V0-P3+: tight coupling with the Governance layer (`.gcc/`) for decision records.

## Version ownership
- **V0 (this directory's core):** constitution + architecture established here.
- Maintained and extended across **all** versions (V0 → V4) under the Lore Protocol.

## Examples
- A new contributor reads `docs/` top-to-bottom to understand the project.
- An AI agent loads the constitution + architecture before making any change.
- A reviewer cites a `docs/` rule (e.g. **NR-3**) to reject a non-patient-disjoint result.

## Boundary rules
- Documents are authoritative; the root README summarizes but does not override them.
- Changes to constitution/architecture documents are **governance events**
  (Rule **NR-5**): they require a recorded, reviewed decision.

---

## Constitution documents (V0-P1)

| Document | Purpose |
|----------|---------|
| [`PROJECT_VISION.md`](./PROJECT_VISION.md) | Why the platform exists; the V4 vision; failure scenarios; philosophy. |
| [`PROJECT_OBJECTIVES.md`](./PROJECT_OBJECTIVES.md) | Objectives, success/failure metrics, acceptance criteria, concern relationships. |
| [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | In / Out / Future / Rejected scope, with rationale. |
| [`VERSION_EVOLUTION_MODEL.md`](./VERSION_EVOLUTION_MODEL.md) | The V0→V4 road; per-version criteria; no-skip rule. |
| [`ARCHITECTURAL_PRINCIPLES.md`](./ARCHITECTURAL_PRINCIPLES.md) | The 12 immutable principles (AP-1…AP-12). |
| [`NON_NEGOTIABLE_RULES.md`](./NON_NEGOTIABLE_RULES.md) | The 15 project laws (NR-1…NR-15). |
| [`GLOSSARY.md`](./GLOSSARY.md) | Canonical terminology. |

## Architecture documents (V0-P2)

| Document | Purpose |
|----------|---------|
| [`architecture/DEPENDENCY_GRAPH.md`](./architecture/DEPENDENCY_GRAPH.md) | Allowed/forbidden imports; dependency flow; extension points. |
| [`architecture/MODULE_BOUNDARIES.md`](./architecture/MODULE_BOUNDARIES.md) | Per-module ownership, I/O, dependencies, forbidden actions. |
| [`architecture/IMPORT_RULES.md`](./architecture/IMPORT_RULES.md) | Explicit allowed/forbidden imports with examples. |
| [`architecture/LAYERED_ARCHITECTURE.md`](./architecture/LAYERED_ARCHITECTURE.md) | The seven layers; information & dependency flow. |
| [`architecture/SYSTEM_CONTEXT.md`](./architecture/SYSTEM_CONTEXT.md) | High-level architecture, subsystem & version relationships. |

## Governance documents (V0-P3)

The **governance framework** — *how the project is allowed to change* — lives in
[`governance/`](./governance/). Start at its index: [`governance/README.md`](./governance/README.md).

| Document | Governs |
|----------|---------|
| [`governance/Architecture_Governance.md`](./governance/Architecture_Governance.md) | How architecture may change; drift detection; audit; rollback; risk tiers. |
| [`governance/AI_Governance.md`](./governance/AI_Governance.md) | Approved AI systems/workflows; prompt standards; AI risk/failure modes; per-interaction requirements. |
| [`governance/Documentation_Governance.md`](./governance/Documentation_Governance.md) | Doc hierarchy, canonical sources, lifecycle, entropy prevention. |
| [`governance/Testing_Governance.md`](./governance/Testing_Governance.md) | Testing standards for V1–V4; validation; release gating. |
| [`governance/Review_Governance.md`](./governance/Review_Governance.md) | Review workflow, risk-based depth, AI-code review, merge approval. |
| [`governance/Release_Governance.md`](./governance/Release_Governance.md) | Release lifecycle, validation, versioning, observability, incidents, rollback. |
| [`governance/Decision_Governance.md`](./governance/Decision_Governance.md) | The ADR framework (required fields, lifecycle, approval, indexing). |
| [`governance/Risk_Governance.md`](./governance/Risk_Governance.md) | Risk categories, scoring, ownership, review cadence. |
| [`governance/RFC_Process.md`](./governance/RFC_Process.md) | RFC lifecycle, template, quality standards. |
| [`governance/Change_Management.md`](./governance/Change_Management.md) | Change classes and their approval/validation/rollback paths. |

## AI Operating System (V0-P4)

The **living state, registries, protocols, templates, and checklists** that let
development survive across years and AI-agent turnover live in the Governance &
Context Control layer: [`../.gcc/README.md`](../.gcc/README.md). A new contributor
or AI agent should **start at** [`../.gcc/MAIN_CONTEXT.md`](../.gcc/MAIN_CONTEXT.md)
and run [`../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../.gcc/CONTEXT_RECOVERY_PROTOCOL.md).

## Recommended reading order
Vision → Objectives → Scope → Version Model → Principles → Rules → Glossary →
Architecture (Layered → System Context → Module Boundaries → Dependency Graph →
Import Rules) → Governance ([`governance/README.md`](./governance/README.md)) →
Operating System ([`../.gcc/MAIN_CONTEXT.md`](../.gcc/MAIN_CONTEXT.md)).
