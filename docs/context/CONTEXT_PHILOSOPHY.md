# CONTEXT PHILOSOPHY

> **Document type:** Context Preservation System (V0-P6) · **Tier 2 (process authority)**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR — [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
> **Enforces:** Principle **AP-9** (versioned decisions), Rule **NR-14** (never lose the rationale / Lore Protocol)
> **Operationalizes:** the live memory in [`../../.gcc/`](../../.gcc/) (Tier 3) — this layer is the *policy*; `.gcc/` holds the *artifacts*.
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This is the root of the **Context Preservation System** (`docs/context/`). Its
mandate is absolute: **no critical knowledge may exist only in a ChatGPT/Claude
conversation, a founder's memory, raw git history, or a PR comment.** Everything
important must become **repository knowledge** — written, versioned, indexed, and
recoverable. The repository is the project's **permanent memory.**

> **Premise:** *Good architecture without memory fails.* A platform built over 5–10
> years by a solo founder + rotating AI agents cannot survive on recall. Context
> preservation is what lets a future agent reconstruct the *entire* project — intent,
> decisions, risks, assumptions, lessons — **without any external conversation.**

---

## 1. What Context Is

**Context** is everything required to *understand and safely change* the project
that is **not** the code/docs themselves: the *why* behind the *what*. It includes:

- **Decisions** and their rationale, alternatives, and consequences (ADRs).
- **Risks** — past, active, resolved, rejected, and the *unknown*.
- **Assumptions** — what we treat as true without proof, and their evidence/status.
- **Knowledge** captured from research, implementation, testing, incidents, reviews,
  AI sessions, and experiments.
- **Lessons learned** and **postmortems** — what worked, what failed, why.
- **State** — where the project is now and where it's going.

Context is distinct from, but feeds, **documentation** (the stated truth) and
**code** (the implemented truth).

## 2. Why Context Matters

- **Code shows *what*; only context preserves *why*.** Without *why*, settled
  questions get re-litigated and invariants get broken unknowingly (context drift —
  [`../PROJECT_VISION.md`](../PROJECT_VISION.md) §10).
- **Memory does not survive turnover.** Founder dormancy and AI-agent rotation
  erase recall; the repository must not depend on it.
- **Trust requires explanation.** A clinical platform must be able to answer "why
  did it do/decide that?" (auditability, AP-8).
- **Foundations compound.** A lost rationale in V0/V1 becomes an unexplained,
  unsafe-to-change constraint in V3/V4.

## 3. Why AI Systems Lose Context

- **Finite context windows:** an agent cannot hold the whole repository; it sees a
  slice and may act on a partial picture.
- **No persistent memory across sessions:** each session starts fresh; "what we
  decided last time" is gone unless it was written down.
- **Plausibility bias:** agents fill gaps with confident guesses rather than
  stopping to recover context (the confident-wrong failure).
- **Conversation ≠ repository:** knowledge created in a chat evaporates when the
  chat ends.

**Defense:** the deterministic [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
+ [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md), and
the rule that **consequential knowledge is written into the repository, not the
chat** ([`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md)).

## 4. Why Repositories Lose Context

- **Entropy:** docs go stale, orphan, or conflict as the repo grows (REPO risk).
- **Silos:** knowledge lives only in one person's head or one tool.
- **Undocumented decisions/risks/assumptions:** the *why* is never captured.
- **Deletion:** history is erased instead of being marked superseded.
- **Drift between memory artifacts and reality:** registries fall behind the code.

**Defense:** the audits in [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md),
the append-only [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md), and
living Tier-3 state files.

## 5. Relationships: Knowledge · Context · Memory · Documentation · Governance · Architecture

```
        ARCHITECTURE ── shaped by ──► DECISIONS (context) ── recorded as ──► MEMORY (.gcc registries)
             ▲                              ▲                                      │
             │ constrains                   │ rationale                            │ recovered via
        GOVERNANCE ───── produces ──────────┘                                      ▼
             │ (decisions/risks/changes)                              CONTEXT RECOVERY (deterministic)
             ▼                                                                     │
        DOCUMENTATION ◄──── stated truth ──── KNOWLEDGE ◄──── captured from ──── research/impl/tests/
                                              (validated, indexed)               incidents/AI/experiments
```

- **Knowledge** is raw understanding; **context** is knowledge organized around
  *why*; **memory** is context **persisted** in the repository (the `.gcc/`
  artifacts); **documentation** is the **stated, canonical** truth.
- **Governance** *produces* context (every decision/risk/change); **context
  preservation** *retains* it; **documentation** *publishes* the parts that are
  canonical; **architecture** is what the decisions shape.
- They are one loop: governance generates → context preserves → recovery restores →
  governance continues. Break any link and the project loses its memory.

## 6. Core Principles of Context Preservation

1. **Repository over conversation.** If it's consequential, it lives in the repo,
   not a chat (the P6 mandate). *"If it isn't written down, it didn't happen."*
2. **Capture at creation.** Context is recorded *as it is created*, not
   reconstructed later from memory (which fails).
3. **Single canonical source.** Each fact lives in exactly one place; everything
   else links (Documentation_Governance §2). No conflicting copies.
4. **Append-only memory.** Decisions/risks/assumptions/postmortems/lessons are
   **never deleted** — superseded items are marked and linked
   ([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)).
5. **Deterministic recovery.** Context must be reconstructable by a fixed procedure
   ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)),
   the same way every time.
6. **Navigable & linked.** Context is a graph: every node reachable, every relation
   traceable ([`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)).
7. **Audited continuously.** Missing/outdated/conflicting/orphaned context is found
   and fixed at every gate, quarter, and after dormancy
   ([`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md)).
8. **Reader-aware.** Written so a future agent with **no prior context** can use it.

## 7. The Context Preservation System (organization)

| Document | Preserves |
|----------|-----------|
| [`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md) | Decisions (ADR lifecycle incl. retirement). |
| [`RISK_MEMORY_SYSTEM.md`](./RISK_MEMORY_SYSTEM.md) | Risks across their whole life (historical→active→resolved→rejected→unknown). |
| [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md) | Assumptions + lifecycle (prevent assumption rot). |
| [`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md) | How knowledge enters the repository (ingest/validate/index/archive). |
| [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md) | Incident learning. |
| [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md) | Reusable lessons (successes & failures). |
| [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md) | Audits for missing/outdated/conflicting/orphaned context. |
| [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md) | What is kept forever / archived / retired (never deleted). |
| [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md) | The complete knowledge graph + traceability + navigation paths. |

## 8. Relationship To Governance, Quality, and the OS
- **Governance (V0-P3)** *produces* the context (ADRs, risks, changes); this system
  *retains* it. It never contradicts a governance policy; on conflict, governance
  governs and the conflict is a defect to fix.
- **Quality (V0-P5)** *depends on* this memory (audits, metrics, and the Context
  Integrity Gate G7 read these artifacts).
- **The GCC OS (V0-P4)** holds the **live artifacts** (Tier 3): `DECISION_REGISTRY`,
  `ACTIVE_RISKS`, `ACTIVE_ASSUMPTIONS`, `LORE_PROTOCOL`, `CONTEXT_RECOVERY_PROTOCOL`,
  `KNOWLEDGE_GRAPH`. This layer is their **policy/framework**.

Changes to this document are governance-class and require an ADR.
