# REPOSITORY KNOWLEDGE MODEL

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative — the **complete** knowledge model (canonical).
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Relationship to the OS graph:** [`../../.gcc/KNOWLEDGE_GRAPH.md`](../../.gcc/KNOWLEDGE_GRAPH.md) is the **operational quick-reference** (Tier 3, read during recovery). **This document is the comprehensive model** (Tier 2) that *adds* the Quality and Context layers and the full traceability + navigation. They must agree; this is canonical for the full model.
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This is the **map of everything and how it connects** — the single place to see the
whole project as a graph, trace any concept to the documents that own it, and
navigate **deterministically** to an answer. It connects all twelve concept
families: **Vision · Objectives · Versions · Subsystems · Decisions · Risks ·
Assumptions · Architecture · Governance · Quality · AI Systems · Context Systems.**

> **Premise:** if every node is reachable and every relation is traceable, then any
> future agent can reconstruct the project and answer any "why?" by **walking the
> graph** — no external conversation required.

---

## 1. The Complete Knowledge Graph

```
                              ┌──────────────────────────┐
                              │  VISION (why we exist)     │  docs/PROJECT_VISION
                              └─────────────┬──────────────┘ realized as
                              ┌─────────────▼──────────────┐
                              │  OBJECTIVES (P1..P6,S,L)    │  docs/PROJECT_OBJECTIVES
                              └───┬──────────────────┬──────┘
                  bounded by      │                  │  measured by
            ┌───────────────┐     │                  │      ┌──────────────────┐
            │ SCOPE          │◄────┘                  └─────►│ SUCCESS/FAILURE   │
            │ in/out/future  │                                │ METRICS          │
            └───────┬────────┘ achieved over versions         └────────┬─────────┘
                    │                                                   │
              ┌─────▼─────────────────────────────────────────────────▼─────┐
              │            VERSIONS  V0 → V1 → V2 → V3 → V4                   │  docs/VERSION_EVOLUTION_MODEL
              └─────┬───────────────────────────────────────────────────────┘
       fixed by     │ structured as                          guarded by
 ┌──────────────────▼───────────┐                  ┌──────────────────────────────┐
 │ PRINCIPLES (AP-1..AP-12)      │◄────enforced by─►│ RULES (NR-1..NR-15)           │
 └──────────────────┬───────────┘                  └───────────────┬──────────────┘
          realized as│                                              │ operated by 4 systems
 ┌───────────────────▼─────────┐    ┌───────────────┬──────────────┼───────────────┐
 │ ARCHITECTURE (7 layers,DAG) │    │ GOVERNANCE     │ QUALITY      │ CONTEXT        │
 │ docs/architecture/*         │    │ docs/governance│ docs/quality │ docs/context   │
 └───────────────────┬─────────┘    │ (how to change)│ (what's good)│ (preserve why) │
        populated by  │              └───────┬────────┴──────┬───────┴───────┬────────┘
              ┌───────▼────────┐             │ produce        │ gate/measure  │ retain
              │ SUBSYSTEMS      │             ▼                ▼               ▼
              │ (modules,       │     ┌───────────────────────────────────────────────┐
              │  per-dir READMEs)│────►│  MEMORY (live, .gcc/): DECISIONS · RISKS ·     │
              └───────┬─────────┘     │  ASSUMPTIONS · DEPENDENCIES · LESSONS ·         │
                      │ changed by    │  POSTMORTEMS · CHANGELOG · STATE                │
                ┌─────▼──────┐        └───────────────────────┬───────────────────────┘
                │ AI SYSTEMS │  produce traceable changes      │ recovered via
                │ (governed) │────────────────────────────────►│ CONTEXT RECOVERY (deterministic)
                └────────────┘                                  └───────────────────────┘
```

## 2. Concept Families → Canonical Owners (where each lives)

| Family | Canonical owner(s) |
|--------|--------------------|
| **Vision** | [`../PROJECT_VISION.md`](../PROJECT_VISION.md) |
| **Objectives / metrics** | [`../PROJECT_OBJECTIVES.md`](../PROJECT_OBJECTIVES.md) |
| **Scope** | [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md) |
| **Versions** | [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) |
| **Principles / Rules** | [`../ARCHITECTURAL_PRINCIPLES.md`](../ARCHITECTURAL_PRINCIPLES.md), [`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md) |
| **Architecture / Subsystems** | [`../architecture/`](../architecture/) + per-module `README.md` |
| **Governance** | [`../governance/`](../governance/) |
| **Quality** | [`../quality/`](../quality/) |
| **Context systems** | `docs/context/` (this directory) |
| **Decisions** | [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) + `.gcc/decisions/` |
| **Risks** | [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) (+ archive) |
| **Assumptions** | [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md) |
| **Dependencies** | [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md) |
| **AI systems** | [`../governance/AI_Governance.md`](../governance/AI_Governance.md) + [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md) |
| **State / history** | [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md), [`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md) |

## 3. Traceability Maps (follow a link from any direction)

### 3.1 Objective → Principle → Rule → Risk → Quality gate
(Extends [`../../.gcc/KNOWLEDGE_GRAPH.md`](../../.gcc/KNOWLEDGE_GRAPH.md) §3 with the gate column.)

| Objective | Principle | Rule | Risk if violated | Quality gate |
|-----------|-----------|------|------------------|--------------|
| Trustworthy detection (P1/P3) | AP-2 | NR-3 | leakage (CLIN/ARCH) | G5 Validation |
| Calibrated uncertainty (P2) | AP-4 | NR-4 | overconfidence (CLIN, RISK-0005) | G5 Validation |
| Reproducibility (P4) | AP-3/AP-6 | NR-9/NR-10 | irreproducibility (TECH) | G4/G5 |
| Traceability (S5) | AP-5/AP-8 | NR-11 | un-auditable output (COMP) | G7 Context |
| Maintainability (P5) | AP-1/AP-7 | NR-6/NR-8 | architecture drift (ARCH, RISK-0003) | G1 Architecture |
| Governance (P6) | AP-9/AP-11 | NR-5/NR-7 | context drift (CTX, RISK-0001) | G8 Governance / G7 |
| Domain-shift robustness (S1) | AP-10 | NR-15 | domain-shift failure (SCALE) | G5 Validation |

### 3.2 Change → records it must leave (the memory trail)
```
 a CHANGE ──► ADR (why)            ──► DECISION_REGISTRY
          ──► RISK (introduced)    ──► ACTIVE_RISKS
          ──► ASM (rested on)      ──► ACTIVE_ASSUMPTIONS
          ──► DEP (added)          ──► DEPENDENCY_REGISTRY
          ──► tests/validation     ──► VALIDATION evidence (G4/G5)
          ──► changelog entry      ──► CHANGELOG (+ git)
          ──► (if AI) AI-TRACE     ──► Lore
          ──► (if failed) postmortem ─► .gcc/postmortems + a LESSON
```

### 3.3 Layer → governing + validating + preserving docs
| Layer/module | Governs | Validates | Preserves |
|--------------|---------|-----------|-----------|
| preprocessing (DSP) | Architecture/Testing Gov | ARCHITECTURE_VALIDATION, TEST_STRATEGY (determinism) | decisions/assumptions on DSP |
| ml | AI/Testing Gov | AI_OUTPUT_VALIDATION, TEST_STRATEGY (ML/clinical) | model-choice ADRs, ASM-0003/0004 |
| evaluation | Testing/Risk Gov | VALIDATION_FRAMEWORK (VC-CLIN) | split-strategy ADRs |
| backend/frontend | Review/Release Gov | CODE_REVIEW_CHECKLISTS, contract tests | API-contract ADRs |
| .gcc / docs | Documentation Gov | DOCUMENTATION_VALIDATION, CONTEXT_AUDIT | all memory systems |

## 4. Deterministic Navigation Paths (how to get an answer)

Each path is a fixed sequence — follow it and you reach the answer the same way
every time. (These extend the recovery read-order in
[`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md).)

| Question | Deterministic path |
|----------|--------------------|
| "What is this project and where is it?" | `MAIN_CONTEXT` → `CURRENT_STATE` → `NEXT_STATE` → `VERSION_STATUS` |
| "Why is X built this way?" | the module README of X → its linked **ADR(s)** → the RFC/changelog |
| "Can I make this change?" | `PROJECT_SCOPE` (NR-13) → `VERSION_STATUS` (NR-12) → `IMPORT_RULES` (NR-8) → `Change_Management` |
| "Is this result trustworthy?" | `VALIDATION_FRAMEWORK` (category) → the evidence → `QUALITY_GATES` G5 |
| "What could go wrong here?" | `ACTIVE_RISKS` (+ archive) → related postmortems/lessons |
| "What are we assuming here?" | `ACTIVE_ASSUMPTIONS` (filter by module) → dependent ADRs |
| "How do I change/release safely?" | `Change_Management` → `QUALITY_GATES` → `RELEASE_CERTIFICATION` |
| "How did past failures inform this?" | `.gcc/postmortems/` + `LESSONS_LEARNED_SYSTEM` (by area) |

## 5. Consistency With The Operational Graph
- [`../../.gcc/KNOWLEDGE_GRAPH.md`](../../.gcc/KNOWLEDGE_GRAPH.md) (Tier 3) is the
  **fast, recovery-time** view (objectives↔architecture↔versions↔risks↔governance↔AI).
- **This document** (Tier 2) is the **complete** model, adding the **Quality** and
  **Context** layers, the traceability maps (§3), and the navigation paths (§4).
- They are kept consistent: a change to the project's structure updates **both**
  (the operational graph during the change; this model as the canonical superset).
  A discrepancy is a CA-3 (conflicting context) finding to reconcile.

## 6. Maintenance
- Update this model whenever a **concept family or a major relationship** changes
  (a new layer, a new system, a new traceability requirement).
- It is read during **deep** context recovery and **onboarding** to convey the
  whole shape before any work.
- Audited by CA-3/CA-4 (no conflict; no orphan node).

## 7. Relationship To Other Documents
- Operational graph: [`../../.gcc/KNOWLEDGE_GRAPH.md`](../../.gcc/KNOWLEDGE_GRAPH.md) · Recovery: [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
- Philosophy/audit: [`CONTEXT_PHILOSOPHY.md`](./CONTEXT_PHILOSOPHY.md), [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md)
- All memory systems in this directory + the registries in [`../../.gcc/`](../../.gcc/)

Changes to this document are governance-class and require an ADR.
