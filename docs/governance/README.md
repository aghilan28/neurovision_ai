# `docs/governance/` — Governance Layer Index (V0-P3)

> **Document type:** Governance Layer (V0-P3) index
> **Status:** Authoritative
> **Owner:** Founder
> **Update procedure:** This index is updated (Documentation change) when a governance document is added/renamed; changes to a governance *policy* are governance-class (ADR — [`Decision_Governance.md`](./Decision_Governance.md)).
> **Parent:** [`../README.md`](../README.md) · **Operating system:** [`../../.gcc/README.md`](../../.gcc/README.md)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This directory holds the **governance framework** — the rules of *how the project
is allowed to change.* Where the **constitution** (`docs/*.md`) defines *why/what*
and the **architecture** (`docs/architecture/*.md`) defines *how it is shaped*,
**governance** defines *how decisions, changes, reviews, releases, risk, and AI
collaboration are conducted* so that architecture, context, and quality **survive
across V0 → V4**.

These documents are **policy** (durable). The **live state** they produce and
consume (registries, current state, decision index) lives in the operating system
under [`../../.gcc/`](../../.gcc/).

---

## Documents

| Document | Governs |
|----------|---------|
| [`Architecture_Governance.md`](./Architecture_Governance.md) | What architecture is; how it may change; drift detection, audit, rollback; risk tiers (A0–A3, AE). |
| [`AI_Governance.md`](./AI_Governance.md) | Approved AI systems and workflows; prompt standards; AI risk/failure modes; per-interaction inputs/outputs/validation/traceability. |
| [`Documentation_Governance.md`](./Documentation_Governance.md) | Doc hierarchy, canonical sources, ownership, lifecycle, entropy prevention. |
| [`Testing_Governance.md`](./Testing_Governance.md) | Testing philosophy and standards for V1–V4; validation; coverage; release gating. |
| [`Review_Governance.md`](./Review_Governance.md) | Review workflow, ownership, risk-based depth, AI-code review, merge approval. |
| [`Release_Governance.md`](./Release_Governance.md) | Release lifecycle/stages, validation, versioning, observability, incident response, rollback. |
| [`Decision_Governance.md`](./Decision_Governance.md) | The ADR framework: required fields, lifecycle, approval, indexing, examples. |
| [`Risk_Governance.md`](./Risk_Governance.md) | Risk categories, scoring, ownership, review cadence; register template. |
| [`RFC_Process.md`](./RFC_Process.md) | RFC lifecycle, template, and quality standards (proposal → closure). |
| [`Change_Management.md`](./Change_Management.md) | Change classes and their approval/validation/rollback paths (the router). |

## How the governance documents fit together

```
            ┌──────────────── CONSTITUTION (docs/*.md) ─ AP-1..AP-12 / NR-1..NR-15 ┐
            │                          │                                           │
            ▼                          ▼                                           ▼
   Architecture_Governance     AI_Governance                          Documentation_Governance
            │  (what may change)   │ (who/how AI changes)                    │ (docs stay true)
            └───────────┬──────────┴───────────────────┬────────────────────┘
                        ▼                               ▼
                  Change_Management  ◄── routes ──►  RFC_Process ──► Decision_Governance (ADR)
                        │                                                   │
            ┌───────────┼───────────────────────────┐                      │ records
            ▼           ▼                            ▼                      ▼
     Review_Governance  Testing_Governance     Risk_Governance     .gcc/ DECISION_REGISTRY
            │           │                            │                  + ACTIVE_RISKS
            └─────► Release_Governance ◄─────────────┘
```

## Reading order (first time)
1. [`Architecture_Governance.md`](./Architecture_Governance.md) (defines the risk
   tiers everything else references)
2. [`Decision_Governance.md`](./Decision_Governance.md) and [`RFC_Process.md`](./RFC_Process.md)
3. [`Change_Management.md`](./Change_Management.md) (the router)
4. [`Review_Governance.md`](./Review_Governance.md), [`Testing_Governance.md`](./Testing_Governance.md), [`Release_Governance.md`](./Release_Governance.md)
5. [`Risk_Governance.md`](./Risk_Governance.md)
6. [`AI_Governance.md`](./AI_Governance.md) (re-read before any AI-driven work)

All changes to documents in this directory are **governance-class** and require an
ADR ([`Decision_Governance.md`](./Decision_Governance.md)).
