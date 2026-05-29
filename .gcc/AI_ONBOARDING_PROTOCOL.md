# AI ONBOARDING PROTOCOL

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (operating protocol)**
> **Status:** Authoritative — the formal procedure for an AI agent's first contribution.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-9, AP-11**, Rules **NR-5, NR-7, NR-13, NR-14**
> **Governs with:** [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md)
> **Last updated:** V0-P4

This is the **formal onboarding procedure** that lets a new AI agent become
productive **without asking the founder.** Completing it means the agent can
recover context, understand the architecture, understand the risks, understand the
current work, and understand the constraints — and then contribute safely under
governance.

> **Hard gate:** an agent that has **not** completed this protocol (and passed the
> validation in §4) is **not cleared to make changes.** Reading is allowed;
> changing is not.

---

## 1. Preconditions
- The agent's system class is **approved** in [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §1
  (Claude, Codex, Cursor, Kiro, MCP, or an explicitly-added future system via ADR).
- The agent can read the repository files.

## 2. Onboarding Sequence (do in order)

### Step 1 — Recover context (mandatory)
Run [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) **in full**
(its deterministic 16-step read order). This is the bulk of onboarding.

### Step 2 — Internalize the laws
From [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md) and
[`../docs/ARCHITECTURAL_PRINCIPLES.md`](../docs/ARCHITECTURAL_PRINCIPLES.md):
be able to recite the rules that most affect day-to-day work — NR-3 (patient-disjoint),
NR-4 (uncertainty), NR-7 (review), NR-8 (boundaries), NR-9 (determinism), NR-12
(no version skip), NR-13 (scope), NR-14 (Lore).

### Step 3 — Learn the boundaries
From [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)
and [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md):
know the **DAG**, the **forbidden imports** (esp. `frontend`→domain, `preprocessing`→anything),
and that the graph is acyclic.

### Step 4 — Learn how to change things
From [`../docs/governance/`](../docs/governance/): know the **change classes**
(Change_Management), how to **propose** (RFC) and **record** (ADR) decisions, the
**review** requirements, and that **AI never self-approves** (NR-7).

### Step 5 — Learn how to leave a trace
From [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md) and
[`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md): know how to annotate commits, emit
the **AI-TRACE block** ([`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §9),
and update state/registers.

### Step 6 — Locate your task's local context
Read the **README of the module** you will touch and any **ADR/RFC** it links.
Confirm the task is **in scope** (NR-13) and **version-gate valid** (NR-12).

## 3. The Agent's Operating Contract (accept before contributing)
By contributing, the agent commits to:
1. **Recover context first** (Step 1) — never act on stale/assumed knowledge.
2. **Obey the constitution** (AP-1…AP-12, NR-1…NR-15) and module boundaries.
3. **Never invent APIs** — verify every symbol against real source; if unverifiable,
   stop and flag (AI_Governance §6).
4. **Stay in scope and in version** (NR-13, NR-12).
5. **Record decisions** (ADR) and **assumptions** ([`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md)),
   and **debt** ([`Risk`/Change_Management], NR-2).
6. **Self-validate** (AI_Governance §7) and **emit the AI-TRACE block**.
7. **Never self-approve** — hand off for human review (NR-7).
8. **Leave it cleaner** — update state files; don't create entropy.
9. **When uncertain, ask/stop** — guessing is the most dangerous action here.

## 4. Onboarding Validation (must pass before changing anything)
The agent must correctly answer the **ten understanding-validation questions** in
[`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md) §3, **plus**:
- [ ] Which AI workflow (Claude/Codex/Cursor/Kiro/MCP) applies to me, and what does
  it require? *(AI_Governance §2)*
- [ ] What must appear in my hand-off for a consequential change? *(AI-TRACE, §3.6)*
- [ ] Who approves my change, and can I approve it myself? *(NR-7 — no)*
- [ ] What do I do if required context is missing? *(stop/ask; record a defect)*

Passing = correct answers to all. Failing on any item = **not cleared**; re-read
the mapped sources. If a question is unanswerable because the docs are insufficient,
the agent's first contribution is to **improve that documentation** (so the next
agent succeeds) — itself a governed change.

## 5. First Contribution Guidance
- Prefer a **small, in-boundary, low-risk** first change to exercise the full loop
  (recover → plan → produce → self-validate → trace → hand off).
- For anything **A2+** (new contract/dependency/architecture/governance), produce an
  **RFC/ADR draft first** and request review — do not implement ahead of approval.

## 6. Relationship To Other Documents
- Context: [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md), [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md)
- Governance: [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md), [`../docs/governance/Review_Governance.md`](../docs/governance/Review_Governance.md)
- Trace: [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md), [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)
- Checklist form: [`CHECKLISTS/ai_onboarding_checklist.md`](./CHECKLISTS/ai_onboarding_checklist.md)

*Onboarding is the difference between an AI agent that strengthens the project and
one that quietly erodes it. It is mandatory, deterministic, and self-validating by
design.*
