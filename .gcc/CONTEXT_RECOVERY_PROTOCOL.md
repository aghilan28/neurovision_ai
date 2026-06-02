# CONTEXT RECOVERY PROTOCOL

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (operating protocol)**
> **Status:** Authoritative — a **deterministic** procedure.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Changes are governance-class (ADR) — the recovery sequence must stay stable and trustworthy.
> **Enforces:** Principle **AP-9**, Rules **NR-5, NR-14**
> **Last updated:** V0-P4

This protocol is how **any** contributor — especially a new AI agent, or the
founder after months away — **reconstructs full project context deterministically**.
"Deterministic" means: *follow these exact steps, in this exact order, and you will
arrive at the same, complete understanding every time.* No guessing, no reliance on
prior-session memory.

> **When to run it:** before *any* work session that follows a context gap (new
> agent, new chat, returning after dormancy, or whenever unsure). AI agents run it
> as Stage 1 of every task ([`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §2.0).

---

## 1. The Deterministic Read Order

Read these **in order**. Do not skip; do not reorder. (Steps map to the reading
order in [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md) §15.)

| # | Read | You will learn |
|---|------|----------------|
| 1 | [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md) | The whole project in minutes: identity, vision, architecture, version position, constraints, invariants. |
| 2 | [`CURRENT_STATE.md`](./CURRENT_STATE.md) | What is true *now*: version/phase, completed work, gaps, repo status. |
| 3 | [`NEXT_STATE.md`](./NEXT_STATE.md) | What's next: immediate objectives, blockers, transition criteria. |
| 4 | [`VERSION_STATUS.md`](./VERSION_STATUS.md) | Per-version status + exit criteria + the no-skip rule. |
| 5 | [`../docs/PROJECT_VISION.md`](../docs/PROJECT_VISION.md) → `OBJECTIVES` → `SCOPE` | Why/what/boundaries. |
| 6 | [`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md) | The road and its gates. |
| 7 | [`../docs/ARCHITECTURAL_PRINCIPLES.md`](../docs/ARCHITECTURAL_PRINCIPLES.md) + [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md) | The principles (AP) and laws (NR) you must obey. |
| 8 | [`../docs/GLOSSARY.md`](../docs/GLOSSARY.md) | Canonical terminology (resolve every unfamiliar term here). |
| 9 | [`../docs/architecture/`](../docs/architecture/) (layered → system context → boundaries → dependency graph → import rules) | The structure and the hard import constraints. |
| 10 | [`../docs/governance/README.md`](../docs/governance/README.md) (+ the domain doc relevant to your task) **and the quality framework [`../docs/quality/README.md`](../docs/quality/README.md)** | How changes are governed and what "good" means (gates/validation). |
| 11 | [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md) | Why things are the way they are (decisions). |
| 12 | [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md) + [`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md) | What's risky and what's unverified. |
| 13 | [`DEPENDENCY_REGISTRY.md`](./DEPENDENCY_REGISTRY.md) | What depends on what (don't add unrecorded edges). |
| 14 | [`KNOWLEDGE_GRAPH.md`](./KNOWLEDGE_GRAPH.md) | How all of the above connects. |
| 15 | [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md) + [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md) **+ the context/memory systems [`../docs/context/README.md`](../docs/context/README.md)** | How to leave a correct trace, and how project memory is preserved/recovered. |
| 16 | **Task-local context:** the README of the module you will touch + any ADR/RFC it links. | The exact boundary and prior decisions for your specific work. |

## 2. How Context Is Reconstructed (what to extract at each layer)
- **Position:** *Which version/phase are we in? What is done? What's next?* (steps 1–4)
- **Intent:** *Why does this exist? What is in/out of scope?* (steps 5–6)
- **Constraints:** *Which invariants/rules can I never violate?* (steps 7–8)
- **Structure:** *What are the modules, boundaries, and allowed imports?* (step 9)
- **Process:** *How do I change things legally?* (step 10)
- **History:** *What was already decided, risked, assumed, and depended upon?* (steps 11–14)
- **Tracing:** *How do I record what I do?* (step 15)
- **Local:** *What governs the exact thing I'm about to touch?* (step 16)

## 3. Understanding Validation (prove recovery succeeded)
Before doing any work, you must be able to answer **all** of these from the
documents (no founder help). If you cannot answer one, **re-read the mapped source;
do not proceed.**

1. What is NeuroVision AI, and what is it explicitly **not**? *(step 1, 5)*
2. What **version and phase** are we in, and what is the immediate next objective?
   *(steps 2–4)*
3. Name **five** non-negotiable rules and the principle each enforces. *(step 7)*
4. State the **dependency direction** and one **forbidden import**. *(step 9)*
5. Why is **patient-disjoint validation** mandatory, and what fails without it?
   *(steps 5,7,8)*
6. What must every **clinical output** carry, and why? *(steps 7–8)*
7. How do you **propose** and **record** a consequential change? *(step 10–11)*
8. Name the **top open risk** and one **open assumption**. *(step 12)*
9. Where do you **record why** you changed something? *(step 15)*
10. What governs the **specific module** you're about to touch? *(step 16)*

A passing recovery = correct answers to all ten. (These mirror the onboarding
validation in [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md).)

## 4. Failure Handling
- **Missing/contradictory context:** record it as a defect/risk; reconcile against
  the canonical source (`docs/` governs); do **not** proceed on a guess.
- **State files look stale** (don't match git reality): treat as a defect; refresh
  `CURRENT_STATE` from evidence and log it before continuing.
- **Unanswerable validation question:** the recovery surface has a gap — fix the
  gap (improve the relevant doc) as the first action, so the next agent succeeds.

## 5. After Dormancy (extra steps)
When resuming after a long gap, additionally:
- Re-run the **documentation audit** (Documentation_Governance §8) and **architecture
  audit** (Architecture_Governance §10) — entropy/drift accumulate silently.
- Re-review **all Critical/High risks** ([`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md)).
- Re-validate **open assumptions** ([`ACTIVE_ASSUMPTIONS.md`](./ACTIVE_ASSUMPTIONS.md)).

## 6. Relationship To Other Documents
- Entry/onboarding: [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md), [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md).
- Governs AI use: [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md).
- Checklist form: [`CHECKLISTS/context_recovery_checklist.md`](./CHECKLISTS/context_recovery_checklist.md).

*This procedure is deterministic by design: same inputs, same order, same recovered
understanding — every time, for every agent.*
