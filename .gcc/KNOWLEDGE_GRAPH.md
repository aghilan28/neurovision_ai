# KNOWLEDGE GRAPH

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated when the relationships between major concepts change.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Update when objectives/architecture/versions/risks/governance relationships change; log it ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P4

This document is the **map of how everything connects**: objectives ↔ architecture
↔ versions ↔ subsystems ↔ risks ↔ dependencies ↔ governance ↔ AI systems. It lets
an agent see the *shape of the whole* before diving into any part, and trace any
concept to the documents that own it.

---

## 1. Top-Level Graph

```
                         ┌───────────────────────────┐
                         │   VISION  (why we exist)    │  docs/PROJECT_VISION
                         └──────────────┬─────────────┘
                                        │ realized as
                         ┌──────────────▼─────────────┐
                         │  OBJECTIVES (P1..P6, S, L)  │  docs/PROJECT_OBJECTIVES
                         └───┬───────────────┬─────────┘
              bounded by     │               │   measured by
              ┌──────────────▼──┐        ┌───▼──────────────┐
              │  SCOPE          │        │ SUCCESS/FAILURE   │
              │  in/out/future  │        │ METRICS          │
              └──────────────┬──┘        └───┬──────────────┘
                             │ achieved over   │
                       ┌─────▼─────────────────▼─────┐
                       │  VERSIONS  V0→V1→V2→V3→V4    │  docs/VERSION_EVOLUTION_MODEL
                       └─────┬───────────────────────┘
              fixed by       │ structured as              guarded by
   ┌─────────────────────────▼──────────┐        ┌────────────────────────────┐
   │ PRINCIPLES (AP-1..AP-12)            │◄──────►│ RULES (NR-1..NR-15)         │
   │ docs/ARCHITECTURAL_PRINCIPLES       │ enforce│ docs/NON_NEGOTIABLE_RULES   │
   └─────────────────────────┬──────────┘        └──────────────┬─────────────┘
                  realized as │                                   │ mechanized by
              ┌───────────────▼───────────────┐      ┌────────────▼─────────────┐
              │ ARCHITECTURE (7 layers, DAG)   │      │ GOVERNANCE (docs/governance)│
              │ docs/architecture/*            │      │ + GCC OS (.gcc/*)          │
              └───────────────┬───────────────┘      └────────────┬─────────────┘
                              │ populated by                       │ tracks
                    ┌─────────▼──────────┐                 ┌───────▼─────────┐
                    │ SUBSYSTEMS/MODULES │                 │ RISKS · DECISIONS│
                    │ (per-dir READMEs)  │                 │ ASSUMPTIONS · DEPS│
                    └─────────┬──────────┘                 └───────┬─────────┘
                              │ changed by                          │ recorded in
                         ┌────▼─────┐                         ┌─────▼──────┐
                         │ AI SYSTEMS│────────────────────────►│ LORE / LOG │
                         │ (governed)│  produce traceable      │ (history)  │
                         └──────────┘  changes                 └────────────┘
```

## 2. Subsystem (Module) Relationships

```
 frontend ─API─► backend ─► ml ─► preprocessing
                    │        │        ▲
                    │        └─► datasets ─┘
                    └─► evaluation ─► {ml, datasets, preprocessing}
 infra: deployment (deploys) · monitoring (observes, drift) — one-way
 cross-cutting: .gcc (governs) · docs (records) — imported by nobody
```
Owners/contracts: each module's `README.md`; edges:
[`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md).

## 3. Objective ↔ Principle ↔ Rule ↔ Risk Threads

| Objective | Principle(s) | Rule(s) | Primary risk if violated |
|-----------|--------------|---------|--------------------------|
| Trustworthy detection (P1/P3) | AP-2 | NR-3 | leakage (CLIN/ARCH) |
| Calibrated uncertainty (P2) | AP-4 | NR-4 | overconfidence (CLIN) — RISK-0005 |
| Reproducibility (P4) | AP-3, AP-6 | NR-9, NR-10 | irreproducibility (TECH) |
| Traceability (S5) | AP-5, AP-8 | NR-11 | un-auditable output (COMP) |
| Maintainability/stability (P5) | AP-1, AP-7 | NR-6, NR-8 | architecture drift (ARCH) — RISK-0003 |
| Governance (P6) | AP-9, AP-11 | NR-5, NR-7 | context drift (CTX) — RISK-0001 |
| Domain-shift robustness (S1) | AP-10 | NR-15 | domain-shift failure (SCALE) |

## 4. Version ↔ Subsystem Activation

| Version | Subsystems that become real | Governance emphasis |
|---------|-----------------------------|---------------------|
| V0 | docs/, .gcc/ (and all module *contracts*) | constitution + governance + OS |
| V1 | preprocessing, datasets, ml, evaluation | determinism, patient-disjoint, UQ |
| V2 | backend, frontend | traceability, API boundary |
| V3 | monitoring, deployment (maturing) | streaming integrity, drift |
| V4 | all hardened | auditability, reliability, deployment |

## 5. Governance ↔ OS Mapping

| Governance policy (docs/governance) | Live OS artifact (.gcc) |
|-------------------------------------|--------------------------|
| Decision_Governance | DECISION_REGISTRY + decisions/ADR-*.md |
| Risk_Governance | ACTIVE_RISKS |
| Architecture_Governance | DEPENDENCY_REGISTRY + architecture audit |
| Change_Management / RFC_Process | CHANGELOG_SYSTEM + RFC/ADR templates |
| Documentation_Governance | this OS's Tier-3 docs + audits |
| AI_Governance | AI_ONBOARDING_PROTOCOL + CONTEXT_RECOVERY_PROTOCOL + AI-TRACE |
| Release_Governance | VERSION_STATUS + release checklist |

## 6. AI Systems ↔ The Graph
Approved AI systems (Claude, Codex, Cursor, Kiro, MCP, future) enter via
[`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md), recover context via
[`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md), act within module
boundaries, and leave **Lore + changelog** traces. They are governed by
[`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) and can
**touch any node above only through a recorded, reviewed change**.

## 7. How To Use This Graph
- **To understand the project:** read top-down (§1).
- **To make a change:** find the affected node, follow its edges to the documents
  that own it, and route the change through Change_Management.
- **To assess impact:** trace a node's outgoing edges — anything reachable may be
  affected.

*This graph is a navigational aid; the linked canonical documents are
authoritative.*
