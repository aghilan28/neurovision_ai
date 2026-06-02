# AI Onboarding Checklist

> **Framework:** [`../AI_ONBOARDING_PROTOCOL.md`](../AI_ONBOARDING_PROTOCOL.md) + [`../../docs/governance/AI_Governance.md`](../../docs/governance/AI_Governance.md)
> A new AI agent completes this **before** making any change. Reading is allowed
> before completion; **changing is not.**

## Preconditions
- [ ] My system class is **approved** (AI_Governance §1) — Claude/Codex/Cursor/Kiro/MCP,
  or added via ADR.

## Sequence
- [ ] **Step 1 — Context recovered:** completed [`context_recovery_checklist.md`](./context_recovery_checklist.md) in full.
- [ ] **Step 2 — Laws internalized:** can recite NR-3, NR-4, NR-7, NR-8, NR-9, NR-12, NR-13, NR-14.
- [ ] **Step 3 — Boundaries learned:** know the DAG + forbidden imports (frontend→domain; preprocessing→anything).
- [ ] **Step 4 — Change process learned:** know change classes, RFC→ADR, review, and that I **never self-approve** (NR-7).
- [ ] **Step 5 — Tracing learned:** know commit annotation + the **AI-TRACE** block + state/register updates.
- [ ] **Step 6 — Local context:** read the target module README + linked ADR/RFC; confirmed in scope (NR-13) + version-valid (NR-12).

## Operating contract (accepted)
- [ ] Recover context first; obey the constitution + boundaries.
- [ ] Never invent APIs — verify every symbol; stop/flag if unverifiable.
- [ ] Stay in scope + version; record decisions/assumptions/debt.
- [ ] Self-validate (AI_Governance §7) + emit AI-TRACE; hand off for human review.
- [ ] Leave it cleaner (update state; no entropy). When uncertain, **ask/stop**.

## Validation (must pass)
- [ ] Answered all 10 context-recovery questions correctly.
- [ ] Which AI workflow applies to me + what it requires (AI_Governance §2).
- [ ] What my hand-off must contain for a consequential change (AI-TRACE).
- [ ] Who approves my change (Founder; **not** me).
- [ ] What I do if context is missing (stop/ask; record a defect).

**Gate:** all ticked ⇒ cleared to contribute (start with a small, in-boundary,
low-risk first change). Any gap ⇒ re-read the mapped sources; if the docs are
insufficient, **improving them is your first contribution.**
