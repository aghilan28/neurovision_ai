# AI-Generated Code Review Checklist

> **Framework:** [`../../docs/governance/AI_Governance.md`](../../docs/governance/AI_Governance.md) §8 + [`../../docs/governance/Review_Governance.md`](../../docs/governance/Review_Governance.md) §8
> Use **in addition** to the general [`review_checklist.md`](./review_checklist.md)
> for any AI-generated change. Bar = **same or higher** than human code (NR-7).

## Trace & context
- [ ] **AI-TRACE block** present and **matches what the diff actually does**
  (agent, context-read, scope, risk-class, decisions, deps, assumptions, invariants,
  self-validation).
- [ ] Evidence the agent **recovered context** (cited the real files it read).

## Anti-hallucination (critical)
- [ ] **Every referenced symbol/file/endpoint resolves to real source** — no invented APIs.
- [ ] No fabricated results/metrics; any claim is sourced.

## Scope & boundaries
- [ ] **No silent scope expansion** — change does only what was requested.
- [ ] **No silent dependency change** — any new dependency is recorded (Dependency Registry, ADR).
- [ ] No forbidden import / cycle introduced (cross-checked against GCC result, NR-8).

## Invariants & records
- [ ] Invariants preserved (patient-disjoint, determinism, uncertainty, provenance).
- [ ] Consequential decisions captured as **ADR** (NR-5); assumptions recorded.
- [ ] For architecture-class AI changes: approved **ADR** + Founder architecture review.

## Approval
- [ ] Reviewed by a **human (Founder)**; the **producing agent did not approve** (NR-7).

> If any anti-hallucination or boundary item fails, **reject** — do not "fix in
> review." Send it back with the specific failure.
