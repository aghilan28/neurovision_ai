# `docs/context/` — Context Preservation System Index (V0-P6)

> **Document type:** Context Preservation System (V0-P6) index · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Index updated (Documentation change) when a context doc is added/renamed; policy changes are governance-class (ADR).
> **Parent:** [`../README.md`](../README.md) · **Quality:** [`../quality/README.md`](../quality/README.md) · **OS (live memory):** [`../../.gcc/README.md`](../../.gcc/README.md)

The **Context Preservation System** — the project's institutional memory policy.
Its mandate: **no critical knowledge may exist only in a chat, founder memory, raw
git history, or a PR comment.** Everything important becomes **repository
knowledge** — written, versioned, indexed, recoverable. These are **Tier 2
(process authority)** documents; the **live memory artifacts** they govern live in
[`../../.gcc/`](../../.gcc/) (Tier 3).

> Where **governance** *produces* context (decisions, risks, changes) and
> **quality** *depends on* it, **this layer preserves it** so a future agent can
> reconstruct the entire project **without any external conversation.**

---

## Documents

| Document | Preserves |
|----------|-----------|
| [`CONTEXT_PHILOSOPHY.md`](./CONTEXT_PHILOSOPHY.md) | What context is; why it's lost; core preservation principles. |
| [`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md) | Decisions — ADR lifecycle + retirement criteria + the decision web. |
| [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md) | Risks across their whole life (active/accepted/resolved/rejected/historical/unknown). |
| [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md) | Assumptions + lifecycle; prevents assumption rot. |
| [`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md) | How knowledge enters the repo (ingest → validate → index → archive). |
| [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md) | Incident learning (blameless, durable). |
| [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md) | Reusable lessons (successes & failures). |
| [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md) | Audits for missing/outdated/conflicting/orphaned/undocumented context. |
| [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md) | What is kept forever / archived / retired (never deleted). |
| [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md) | The complete knowledge graph + traceability maps + deterministic navigation paths. |

## How context preservation fits together
```
                       CONTEXT_PHILOSOPHY  (why memory matters; principles)
                                 │
        ┌───────────────┬────────┼─────────────┬─────────────────┐
        ▼               ▼        ▼              ▼                 ▼
  DECISION_MEMORY  RISK_MEMORY  ASSUMPTION_   POSTMORTEM_     LESSONS_LEARNED
                                 MEMORY        FRAMEWORK         SYSTEM
        │               │        │              │                 │
        └───────────────┴────────┴──────────────┴─────────────────┘
                                 │ all fed by
                       KNOWLEDGE_CAPTURE_FRAMEWORK  (the on-ramp)
                                 │ kept honest by / kept forever by
                 ┌───────────────┴────────────────┐
                 ▼                                 ▼
        CONTEXT_AUDIT_SYSTEM              MEMORY_RETENTION_POLICY
                 │                                 │
                 └──────────────┬──────────────────┘ all mapped by
                                ▼
                    REPOSITORY_KNOWLEDGE_MODEL  (the complete graph + navigation)
                                │ feeds
                    .gcc/CONTEXT_RECOVERY_PROTOCOL (deterministic recovery)
```

## Live artifacts these policies govern (in `.gcc/`, Tier 3)
- Decisions: [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) (+ `.gcc/decisions/`)
- Risks: [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)
- Assumptions: [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md)
- Lore loop: [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md)
- Recovery: [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
- Operational graph: [`../../.gcc/KNOWLEDGE_GRAPH.md`](../../.gcc/KNOWLEDGE_GRAPH.md)
- Templates: [`../../.gcc/TEMPLATES/`](../../.gcc/TEMPLATES/) (ADR, RISK, ASSUMPTION, POSTMORTEM, LEARNING, …)

## Reading order (first time)
1. [`CONTEXT_PHILOSOPHY.md`](./CONTEXT_PHILOSOPHY.md)
2. [`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md)
3. [`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md), [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md), [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md)
4. [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md), [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md)
5. [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md), [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)
6. [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)

All changes to documents in this directory are **governance-class** and require an
ADR ([`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
