# REVIEW GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Review Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-7, AP-8, AP-11, AP-12** and Rules **NR-5, NR-7, NR-8** ([`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document defines **how changes are reviewed before they enter the platform.**
Review is the human checkpoint that makes governance real: it is where the
constitution, boundaries, and decisions are verified against an actual change.
Because AI agents are first-class contributors, **all code — human or AI — is
reviewed** (Rule **NR-7**), and AI-generated changes are held to the same or a
higher bar.

---

## 1. Review Workflow

```
 change proposed ─► GCC automated checks ─► risk classification ─► human review ─► decision
                          │                                              │
                     fail │                                       ┌── request changes
                          ▼                                       │
                  fix before review                               ├── approve ─► merge
                                                                  └── reject/escalate
```

1. **Automated first.** GCC checks (imports/boundaries/acyclicity) and tests must
   pass **before** human review begins — humans review *meaning*, machines check
   *mechanics* (Principle **AP-11**).
2. **Classify risk** (Architecture_Governance §13.1: A0…A3, AE) — this sets review
   depth (§4).
3. **Human review** by the appropriate reviewer (§2), using the right checklist (§9).
4. **Decision:** approve / request-changes / reject / escalate.
5. **Merge** only on approval + green checks + (for A2+) a recorded ADR.

## 2. Review Ownership

| Change class | Required reviewer |
|--------------|-------------------|
| A0 Editorial / A1 Minor | Reviewer (Founder, or Founder-supervised AI assist) |
| A2 Major (new contract / new dependency) | **Founder** |
| A3 Architecture-critical | **Founder** (mandatory; never delegated) |
| AE Emergency | **Founder** (retroactive deep review + ADR ≤72h) |
| Governance-document change | **Founder** (ADR) |

**An AI agent may *assist* review (e.g. summarize a diff, flag a boundary risk)
but may never be the *sole approver* of any change** (Rule **NR-7**). The
producing agent never approves its own output.

## 3. Review Requirements (every review)

The reviewer verifies, at minimum:
- [ ] **Scope:** the change matches its stated intent; no scope expansion (NR-13).
- [ ] **Boundaries:** no forbidden import / no cycle (NR-8); target boundary respected.
- [ ] **Invariants:** patient-disjoint, determinism, calibrated uncertainty,
  reproducibility, traceability preserved where relevant (AP-2/3/4/5/6, NR-3/4/9/10/11).
- [ ] **Decisions:** any consequential choice has an ADR (NR-5).
- [ ] **Debt:** any shortcut is recorded with a repayment plan (NR-2).
- [ ] **Dependencies:** any new/changed dependency is recorded (Dependency Registry).
- [ ] **Tests:** required tests exist/updated and pass ([`Testing_Governance.md`](./Testing_Governance.md)).
- [ ] **Docs:** affected docs/READMEs updated in the same change set.
- [ ] **Traceability:** for AI changes, the AI-TRACE block is present and accurate
  ([`AI_Governance.md`](./AI_Governance.md) §9).
- [ ] **Changelog:** the change is logged ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)).

## 4. Risk-Based Review Depth

| Tier | Depth | What the reviewer does |
|------|-------|------------------------|
| **A0** Editorial | Light | Confirm no meaning/structure change; confirm logged. |
| **A1** Minor | Standard | Full §3 checklist within one module's boundary. |
| **A2** Major | Deep | §3 + verify the new contract/dependency + ADR + Dependency Registry. |
| **A3** Architecture | Deepest | §3 + Architecture review checklist (Architecture_Governance §12) + RFC/ADR + invariant + acyclicity audit. |
| **AE** Emergency | Post-hoc deep | Minimal safe review to stop the bleeding, then full deep review + retro ADR ≤72h. |

Depth scales with **blast radius and reversibility**, consistent with
survivability-over-speed (AP-12).

## 5. Merge Approval Process
- Merge requires: **green GCC checks + green tests + approving review** (+ ADR for
  A2+).
- The merge references the ADR/RFC/change record where applicable.
- Merge to protected branches follows [`../../.gcc/BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md).
- A merge that bypasses checks is a governance violation and is reverted.

## 6. Cross-Module Review Process
A change touching **more than one module** requires:
- Explicit enumeration of every module touched and every edge exercised.
- Confirmation that each exercised edge is **allowed** (the diff introduces no new
  edge without an ADR).
- Deeper review (**A2 minimum**); if it changes any edge, it is **A3**.

## 7. Architecture Review Triggers
A review escalates to **A3 / architecture review** automatically when the change:
- adds/removes/renames a module or layer;
- adds/redirects a dependency edge or affects acyclicity;
- alters a module boundary or public contract;
- touches a cross-version invariant or an import rule.
(See Architecture_Governance §2 for the full definition.)

## 8. AI-Generated Code Review Requirements
In addition to §3, for AI-generated changes the reviewer:
- cross-checks the GCC result against the diff (don't trust, verify);
- confirms **no hallucinated symbols** — every reference resolves to real source;
- confirms **no silent scope/dependency expansion**;
- confirms the **AI-TRACE block** matches what the diff actually does;
- holds the change to the **same or higher** bar as human code (NR-7).

## 9. Review Checklists
- **General review:** [`../../.gcc/CHECKLISTS/review_checklist.md`](../../.gcc/CHECKLISTS/review_checklist.md)
- **AI-generated review:** [`../../.gcc/CHECKLISTS/ai_review_checklist.md`](../../.gcc/CHECKLISTS/ai_review_checklist.md)
- **Architecture review:** [`../../.gcc/CHECKLISTS/architecture_change_checklist.md`](../../.gcc/CHECKLISTS/architecture_change_checklist.md)
- **Release review:** [`../../.gcc/CHECKLISTS/release_checklist.md`](../../.gcc/CHECKLISTS/release_checklist.md)

## 10. Relationship To Other Governance Documents
- Change paths: [`Change_Management.md`](./Change_Management.md) · Decisions: [`Decision_Governance.md`](./Decision_Governance.md)
- Testing: [`Testing_Governance.md`](./Testing_Governance.md) · Releases: [`Release_Governance.md`](./Release_Governance.md)
- AI: [`AI_Governance.md`](./AI_Governance.md) · Branching: [`../../.gcc/BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md)

Changes to this document are governance-class and require an ADR.
