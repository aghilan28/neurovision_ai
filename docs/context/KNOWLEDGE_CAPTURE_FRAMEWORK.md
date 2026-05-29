# KNOWLEDGE CAPTURE FRAMEWORK

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Operationalizes:** [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) (the capture loop) and the P6 mandate.
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This framework defines **how knowledge enters the repository** — turning transient
understanding (from a chat, an experiment, a review) into **durable, indexed,
recoverable repository knowledge.** It is the on-ramp for everything the other
context systems preserve.

> **Premise (the P6 mandate):** important knowledge must **never** live only in a
> ChatGPT/Claude conversation, founder memory, raw git history, or a PR comment.
> Capture is the act of moving it into the repository.

---

## 1. Knowledge Sources

Knowledge arrives from many places; each has a capture destination:

| Source | Example | Captured as / into |
|--------|---------|--------------------|
| **Research** | A finding about EEG leakage traps or UQ behavior | Lesson / assumption / ADR; Glossary if new term |
| **Implementation** | A non-obvious design choice while coding | ADR (if consequential) + commit annotation |
| **Testing** | A discovered failure mode / invariant gap | Test + lesson; risk if recurring |
| **Incidents** | An outage/drift/safety event (V3+) | Postmortem → risk + prevention + lesson |
| **Architecture reviews** | A boundary/coupling insight | ADR + architecture doc update |
| **AI sessions** | Reasoning/output from Claude/Codex/Cursor/Kiro/MCP | **AI-TRACE** (Lore) + any ADR/assumption it produced |
| **Experiments** | A benchmark/ablation result | Result recorded in `evaluation/` + lesson + assumption verification |

## 2. The Capture Pipeline

```
 CAPTURE ─► VALIDATE ─► INDEX ─► (later) ARCHIVE
```

### 2.1 Ingestion (Capture)
- **Trigger:** any consequential knowledge is created (a decision, a result, a
  failure, a learning, an assumption, a new term).
- **Action:** write it into the **correct canonical home** (see §3), **at creation**
  — not "later." For AI work, the **AI-TRACE block** is emitted with the change
  ([`../governance/AI_Governance.md`](../governance/AI_Governance.md) §9).
- **Rule:** if it is consequential and lives only in a conversation, it is **not yet
  captured** — capture it before the work is considered done.

### 2.2 Validation
Before knowledge is trusted as repository truth:
- **Correct & sourced** — claims are evidenced, not asserted (mirrors
  [`../quality/VALIDATION_FRAMEWORK.md`](../quality/VALIDATION_FRAMEWORK.md)).
- **Single canonical source** — it does not duplicate/contradict an existing record
  (Documentation_Governance §2); on conflict, reconcile.
- **Termed** — any new consequential term is added to the Glossary (NR-14).
- **Classified** — routed to the right home (§3) with the right type
  (decision/risk/assumption/lesson/postmortem).

### 2.3 Indexing
- Add the artifact to its **registry/index** (Decision Registry, Active Risks,
  Active Assumptions, lessons/postmortems index) and **link it bidirectionally**
  to related artifacts (the decision web; [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)).
- Add a **changelog** entry ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)).
- Ensure it is **reachable from an index** (no orphans — Documentation Gate G2).

### 2.4 Archival
- When knowledge is superseded/retired, it is **marked and archived (kept, linked)**,
  never deleted ([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)).

## 3. Canonical Homes (where each kind of knowledge lives)

| Knowledge kind | Canonical home |
|----------------|----------------|
| Decision + rationale | ADR (`.gcc/decisions/`) + [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) |
| Risk | [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) (+ archive) |
| Assumption | [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md) |
| Lesson | [`LESSONS_LEARNED_SYSTEM.md`](./LESSONS_LEARNED_SYSTEM.md) → `.gcc/learnings/` |
| Postmortem | [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md) → `.gcc/postmortems/` |
| Terminology | [`../GLOSSARY.md`](../GLOSSARY.md) |
| Experiment result | `evaluation/` outputs (V1+) + a lesson/assumption-verification |
| Project state | [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md) / [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md) |
| Change history | [`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md) + git |

**Rule:** each fact has **exactly one** canonical home; everything else links.

## 4. Capture Responsibilities
- **The contributor** (human or AI) captures knowledge **as part of completing the
  work** — capture is not a separate later task.
- **AI agents** must capture via AI-TRACE + the appropriate artifact; they may
  **draft** but a human approves substantive knowledge that changes shared truth (NR-7).
- **The reviewer** confirms capture happened (the Context Integrity Gate G7) before
  approving.

## 5. Anti-Patterns (capture failures to reject)
- "It's in the chat / the PR thread" → **not captured**; move it into the repo.
- "I'll document it later" → later rarely comes; capture at creation.
- Duplicating a fact in two docs → creates conflict; link to the canonical source.
- A new term used but undefined → add to the Glossary (NR-14).
- A result reported but not reproducible/recorded → not valid knowledge (NR-10).

## 6. Recovery & Audit
- **Recovery:** captured + indexed knowledge is exactly what
  [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
  reads to reconstruct the project — capture quality determines recovery quality.
- **Audit (G7):** the context audit ([`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md))
  finds knowledge that was created but not captured (silos), orphaned, or duplicated.

## 7. Relationship To Other Documents
- Lore loop: [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) · Philosophy: [`CONTEXT_PHILOSOPHY.md`](./CONTEXT_PHILOSOPHY.md)
- Destinations: decision/risk/assumption/lesson/postmortem systems in this directory
- Graph/retention: [`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md), [`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)

Changes to this document are governance-class and require an ADR.
