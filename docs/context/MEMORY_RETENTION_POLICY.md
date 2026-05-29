# MEMORY RETENTION POLICY

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Rule **NR-14** (never lose the rationale), Principle **AP-9**; aligns with [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §7 (lifecycle)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This policy defines **what the repository keeps, for how long, and how** — so that
the project's memory is **durable by default** and nothing important is ever lost.
Its governing rule is simple and strict: **append-only memory; never delete the
*why*.**

> **Premise:** deletion destroys context. The cost of keeping a record is near
> zero; the cost of losing a rationale is a re-litigated decision or a broken
> invariant years later. When in doubt, **keep it.**

---

## 1. Retention Tiers

| Tier | What | Policy |
|------|------|--------|
| **Permanent (never delete)** | Decisions (ADRs), risks (incl. resolved/rejected), assumptions, postmortems, lessons, the changelog, the Glossary, constitution (Tier 0), architecture (Tier 1), governance/quality/context policy (Tier 2). | **Retained forever.** Superseded items are **marked + linked**, never removed. |
| **Living (kept current; history in git)** | Tier-3 state files (`CURRENT_STATE`, `NEXT_STATE`, `VERSION_STATUS`, `ROADMAP_STATUS`, registries, `KNOWLEDGE_GRAPH`). | **Continuously updated**; prior states preserved by git history. |
| **Archivable (kept, may be moved)** | Resolved/rejected risks; superseded docs/ADRs; closed postmortems; old working docs. | **Moved to an archive** (still reachable + linked); never deleted. |
| **Retirable (ends active use, record kept)** | A doc/decision whose context has fully dissolved. | Marked **Retired** with the reason/criteria met; the record is kept. |
| **Ephemeral (not memory; may be discarded)** | Scratch notes, local experiment junk, chat transcripts **after** their consequential content is captured. | **Discardable only after capture** ([`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md)). |

## 2. What Is Retained Forever (the non-negotiable core)
- **Every decision and its rationale** (ADRs) — the project's *why* (AP-9/NR-5).
- **Every risk's history** — including resolved and rejected, so hazards aren't re-discovered.
- **Every assumption's history** — including refuted, so we remember what we once believed.
- **Every postmortem and lesson** — so failures pay off once and successes repeat.
- **The changelog + git history** — the traceable spine of what changed and why.
- **The Glossary and the constitution** — canonical meaning and law.

> These are retained **regardless of version, age, or apparent obsolescence.** An
> obsolete decision still explains why something *was* a certain way — which a
> future agent may need to safely change it.

## 3. What Can Be Archived
Anything in the **Archivable** tier (resolved/rejected risks, superseded docs/ADRs,
closed postmortems). Archival means **relocated for tidiness, not removed**:
- The item is **marked** (state + date) and **linked** to its successor (if any).
- It remains **reachable** from a history/archive index (no orphans — CA-4).
- Inbound links are updated to point to the current canonical source.

## 4. What Can Be Retired
A doc/decision whose context has fully dissolved (its **Retirement Criteria** were
met — [`DECISION_MEMORY_SYSTEM.md`](./DECISION_MEMORY_SYSTEM.md) §3). Retirement
**ends active use** but **keeps the record** (marked `Retired`, with the reason).
Constitutional baselines (AP/NR-derived) **do not retire** — they may only be
revisited via governance.

## 5. What Must Never Be Deleted
- Decisions, risks, assumptions, postmortems, lessons (any state).
- Superseded authoritative docs (Tier 0–2) and ADRs.
- The changelog and git history.
- Anything another artifact links to (deleting it would orphan the link).

**Deletion of any of the above is a governance violation** and a **CTX** failure
([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md)). The correct
operation is **supersede/retire/archive**, never delete.

## 6. Lifecycle Rules (how items move between tiers)
```
 CREATED ─► ACTIVE ─► (superseded/resolved/retired) ─► ARCHIVED/RETIRED (kept, linked)
                                   │
                              ephemeral? ── capture consequential content ──► then discardable
```
- Movement is **append-only and recorded** (changelog; ADR if Tier 0–2).
- Every move preserves **reachability** (CA-4) and **bidirectional links** (the
  knowledge model).
- Git is the immutable backing store; tags are immutable (Release_Governance §6).

## 7. Why This Policy Exists
A 5–10 year, solo-founder + AI-agent project cannot rely on memory; it relies on
**retained, recoverable records.** This policy guarantees that the inputs to
[`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
**still exist** whenever a future agent needs them — even after long inactivity.

## 8. Relationship To Other Documents
- Doc lifecycle/retirement: [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §7, [`../quality/DOCUMENTATION_VALIDATION.md`](../quality/DOCUMENTATION_VALIDATION.md) §5
- Memory systems: decision/risk/assumption/postmortem/lesson docs in this directory
- Audit/recovery: [`CONTEXT_AUDIT_SYSTEM.md`](./CONTEXT_AUDIT_SYSTEM.md), [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)

Changes to this document are governance-class and require an ADR.
