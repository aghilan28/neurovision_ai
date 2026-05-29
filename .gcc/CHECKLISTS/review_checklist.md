# Review Checklist (general)

> **Framework:** [`../../docs/governance/Review_Governance.md`](../../docs/governance/Review_Governance.md)
> Use for **every** change before approval. Depth scales with risk tier
> (A0 light → A3 deepest). Architecture/AI changes also use their specific checklists.

## Pre-review (automated first)
- [ ] GCC checks green (imports/boundaries/acyclicity).
- [ ] Required tests green ([`../../docs/governance/Testing_Governance.md`](../../docs/governance/Testing_Governance.md)).
- [ ] Risk tier classified (A0–A3/AE) → review depth set.

## Scope & intent
- [ ] Change matches its stated intent; **no scope expansion** (NR-13).
- [ ] In scope and **version-gate valid** (NR-12).

## Boundaries & invariants
- [ ] No forbidden import / no cycle; target boundary respected (NR-8).
- [ ] Relevant invariants preserved: patient-disjoint (NR-3), uncertainty (NR-4),
  determinism (NR-9), reproducibility (NR-10), traceability (NR-11).

## Records
- [ ] Consequential decision has an **ADR** (NR-5).
- [ ] Any shortcut has a **debt record** + repayment plan (NR-2).
- [ ] New/changed **dependency** recorded (Dependency Registry).
- [ ] New **term** added to the Glossary (NR-14).

## Quality
- [ ] Required **tests** exist/updated and pass.
- [ ] Affected **docs/READMEs** updated in the same change set.
- [ ] No introduced **entropy** (no orphan/conflicting/duplicated docs).

## Traceability & approval
- [ ] **Changelog** entry present and accurate ([`../CHANGELOG_SYSTEM.md`](../CHANGELOG_SYSTEM.md)).
- [ ] For AI changes: **AI-TRACE** block present and matches the diff → use
  [`ai_review_checklist.md`](./ai_review_checklist.md).
- [ ] Approver is **not** the producing agent (NR-7); Founder approval for A2+.

A failed mandatory item = **request changes / block** (not "approve with comment").
