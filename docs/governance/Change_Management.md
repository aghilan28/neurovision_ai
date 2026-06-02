# CHANGE MANAGEMENT

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Change Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-1, AP-7, AP-9, AP-11, AP-12** and Rules **NR-1, NR-2, NR-5, NR-6, NR-8, NR-12, NR-13**
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document is the **router** for all changes: it classifies any proposed change
and sends it down the correct approval, validation, and rollback path. It ties
together the RFC process, ADRs, review, testing, and risk. **Every change has a
class; every class has a path; no change escapes a path.**

---

## 1. Change Categories

| Class | Definition | Risk tier (Architecture_Governance §13.1) | RFC? | ADR? |
|-------|------------|-------------------------------------------|------|------|
| **Documentation** | Edits to docs that don't change a Tier 0–2 *meaning*. | A0/A1 | No | Only if it changes a Tier 0–2 meaning |
| **Minor** | In-boundary implementation; no contract/invariant/dependency effect. | A1 | No | No |
| **Major** | New public contract, new external dependency, or consequential method choice. | A2 | **Yes** | **Yes** |
| **Architecture** | Module/layer/edge/boundary/invariant/import-rule change. | A3 | **Yes** | **Yes (Founder)** |
| **Governance** | Change to a `docs/governance/*` or constitution document, or to `.gcc/` policy. | A3 | **Yes** | **Yes (Founder)** |
| **Emergency** | Time-critical fix to a live problem (V3+). | AE | Retro | **Retro ADR ≤72h** |

> A change that fits multiple classes takes the **highest** one.

## 2. Approval Paths

```
 Documentation (no-meaning) ─► Reviewer ─► merge (logged)
 Minor ─────────────────────► Reviewer ─► tests+GCC green ─► merge (logged)
 Major ─────► RFC ─► ADR (Founder) ─► implement ─► deep review ─► tests+GCC ─► merge
 Architecture ─► RFC ─► ADR (Founder) ─► implement ─► architecture review ─► audit ─► merge
 Governance ──► RFC ─► ADR (Founder) ─► update doc ─► review ─► merge ─► propagate consistency
 Emergency ──► mitigate now ─► record incident ─► retro RFC/ADR ≤72h ─► deep review ─► reconcile
```

- All paths end in a **changelog entry** ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)).
- **Architecture/Governance** changes are **Founder-approved only** (NR-7) and
  must **propagate consistency** (update every dependent doc/registry in the same
  change set).
- **No path** permits skipping a version gate (NR-12) or working out of scope
  (NR-13); those are rejected at classification.

## 3. Validation Requirements By Class

| Class | Required validation before merge |
|-------|----------------------------------|
| Documentation | Doc audit checks (links/terms/consistency); changelog. |
| Minor | Module tests + GCC checks green; self/standard review. |
| Major | Contract/dependency tests; ADR present; Dependency Registry updated; deep review. |
| Architecture | Boundary + acyclicity + invariant tests; architecture audit; ADR; deep review. |
| Governance | Cross-document consistency check; ADR; review; propagate. |
| Emergency | Minimal safe validation now; full validation + retro ADR within 72h. |

(Test specifics: [`Testing_Governance.md`](./Testing_Governance.md). Review depth:
[`Review_Governance.md`](./Review_Governance.md).)

## 4. Rollback Requirements By Class

| Class | Rollback expectation |
|-------|----------------------|
| Documentation | Git revert; restore prior doc; relog. |
| Minor | Git revert of the change set. |
| Major | Revert + restore prior contract/dependency state; update Dependency Registry; note in ADR. |
| Architecture | Architecture_Governance §11 (revert + restore architecture docs + registry; possible incident). |
| Governance | Revert doc to prior authoritative version; reconcile dependents; record. |
| Emergency | Re-deploy last known-good (Release_Governance §9); incident + postmortem. |

**Every Major/Architecture/Governance/Emergency change records its rollback
*before* approval.** A change with no rollback is not approvable.

## 5. Technical-Debt Handling (cross-cutting)
If any change knowingly takes a shortcut, it **must** create a debt record
(what/why/risk/repayment plan) — undocumented debt is forbidden (NR-2). The debt
record links to the change and (if it accepts risk) to a `RISK-` entry. The V0
debt budget is **zero**.

## 6. The Change Record (every change)
Each change produces a record (changelog entry; template:
[`../../.gcc/TEMPLATES/CHANGE_RECORD_TEMPLATE.md`](../../.gcc/TEMPLATES/CHANGE_RECORD_TEMPLATE.md))
capturing: id, class, summary, modules touched, linked RFC/ADR/RISK/DEP ids,
validation result, reviewer, and rollback reference. For AI-made changes it
includes the **AI-TRACE block** ([`AI_Governance.md`](./AI_Governance.md) §9).

## 7. Classification Decision Aid
Ask, in order:
1. Does it change a **Tier 0–2 document's meaning**, an **invariant**, a **module
   boundary/edge**, or an **import rule**? → **Architecture or Governance** (A3).
2. Does it add a **new contract/dependency** or a **consequential method**? → **Major** (A2).
3. Is it a **live-incident fix** that can't wait? → **Emergency** (AE).
4. Is it **in-boundary** with no contract/invariant/dependency effect? → **Minor** (A1).
5. Is it a **non-meaning doc edit**? → **Documentation** (A0/A1).
When two apply, choose the **higher** class. When unsure, choose the **higher**.

## 8. Relationship To Other Governance Documents
- Proposals/decisions: [`RFC_Process.md`](./RFC_Process.md), [`Decision_Governance.md`](./Decision_Governance.md)
- Review/Testing/Release: [`Review_Governance.md`](./Review_Governance.md), [`Testing_Governance.md`](./Testing_Governance.md), [`Release_Governance.md`](./Release_Governance.md)
- Architecture/Risk: [`Architecture_Governance.md`](./Architecture_Governance.md), [`Risk_Governance.md`](./Risk_Governance.md)
- Logging/branching: [`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md), [`../../.gcc/BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md)

Changes to this document are governance-class and require an ADR.
