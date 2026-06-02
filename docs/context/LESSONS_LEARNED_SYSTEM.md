# LESSONS LEARNED SYSTEM

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR) for the *system*; capturing a *lesson* is routine.
> **Home:** `.gcc/learnings/` · **Template:** [`../../.gcc/TEMPLATES/LEARNING_TEMPLATE.md`](../../.gcc/TEMPLATES/LEARNING_TEMPLATE.md)
> **Lore loop:** [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) §6

A **permanent learning registry**: the place where insights — from successes,
failures, and surprises — become **reusable** so the project (and every future AI
agent) gets smarter over time instead of repeating itself. Lessons differ from
postmortems (incident-specific) and ADRs (decisions): a **lesson is transferable
knowledge** intended to inform *future* work.

> **Premise:** a project that does not accumulate lessons re-pays for every mistake
> and re-discovers every success. Lessons are how experience compounds.

---

## 1. What Is Captured

| Lesson type | Example |
|-------------|---------|
| **Successes** | A pattern that worked well and should be repeated (e.g. "test-first determinism for preprocessing caught regressions early"). |
| **Failures** | A mistake and how to avoid it (often distilled from a postmortem). |
| **Unexpected outcomes** | A surprise that changes our mental model (e.g. a method that looked promising but leaked). |
| **Architectural lessons** | Insights about boundaries/coupling/evolution. |
| **AI lessons** | What works/fails when collaborating with Claude/Codex/Cursor/Kiro/MCP (prompting, verification, scope). |
| **Testing lessons** | Effective test designs; gaps that let defects through. |
| **Operational lessons** | Build/release/monitoring insights (V3+). |

Each lesson (template fields): **ID (`LEARN-NNNN`) · what was learned · context ·
evidence · implication for the project · links** (ADR/RISK/ASM/module/postmortem).

## 2. Lesson Lifecycle

```
 OBSERVE (success/failure/surprise) ─► CAPTURE (LEARN-NNNN) ─► VALIDATE (evidenced?) ─►
 INDEX (link to where it applies) ─► APPLY (informs future work) ─► (revise/supersede as understanding grows)
```

- **Capture** at the moment of insight (during implementation, review, testing,
  experiment, or from a postmortem) — not reconstructed later.
- **Validate:** the lesson is evidenced (not a hunch); if it changes shared
  understanding, reflect it in the relevant doc/Glossary; if it changes a decision,
  open an ADR; if it invalidates an assumption, update
  [`ASSUMPTION_MEMORY_SYSTEM.md`](./ASSUMPTION_MEMORY_SYSTEM.md).
- **Index & link:** connect the lesson to the modules/decisions/risks it informs so
  it surfaces during future work in that area.
- **Apply:** lessons are an **input to planning and to AI onboarding** — a new agent
  reads relevant lessons before working in an area.
- **Revise:** lessons can be refined or superseded as understanding deepens
  (append-only; the prior version is kept and linked).

## 3. Making Lessons Reusable (the central job)
A lesson is only valuable if it is *found and applied* at the right moment. Mechanisms:
1. **Linked to where it applies** — a lesson about preprocessing leakage links from
   `preprocessing/`/`evaluation/` context and from the relevant risks.
2. **Surfaced in onboarding** — [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md)
   step 6 (task-local context) includes reading lessons relevant to the target area.
3. **Feeds prevention** — failure-derived lessons pair with a guarding check
   ([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md) §5) so the
   lesson is *enforced*, not just *remembered*.
4. **Promoted when general** — a recurring lesson that should bind future work is
   promoted into a **rule/principle/governance** change via ADR (e.g. it becomes a
   review-checklist item).

## 4. Relationship to Postmortems, Decisions, Risks, Assumptions
- **Postmortem → Lesson:** every postmortem yields ≥1 lesson ([`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md) §3).
- **Lesson → Decision:** a lesson that should change how we build triggers an ADR.
- **Lesson → Risk:** a lesson revealing a hazard updates the risk register.
- **Lesson → Assumption:** a lesson can confirm/refute an assumption.
Lessons are connective tissue across the memory systems; the knowledge model
([`REPOSITORY_KNOWLEDGE_MODEL.md`](./REPOSITORY_KNOWLEDGE_MODEL.md)) shows the links.

## 5. Retention
Lessons are **permanent** ([`MEMORY_RETENTION_POLICY.md`](./MEMORY_RETENTION_POLICY.md)):
never deleted; superseded lessons are marked and linked to their successor.

## 6. Recovery & Audit
- **Recovery:** lessons relevant to a task area are read during onboarding/recovery.
- **Audit (G7):** every postmortem produced a lesson; lessons are linked to where
  they apply (not orphaned); failure-derived lessons have an associated prevention.

## 7. Relationship To Other Documents
- Capture/postmortems: [`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md), [`POSTMORTEM_FRAMEWORK.md`](./POSTMORTEM_FRAMEWORK.md)
- Decisions/risks/assumptions: the respective memory systems in this directory
- Template/Lore: [`../../.gcc/TEMPLATES/LEARNING_TEMPLATE.md`](../../.gcc/TEMPLATES/LEARNING_TEMPLATE.md), [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md) §6

Changes to this document are governance-class and require an ADR.
