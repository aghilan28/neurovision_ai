# CONTEXT AUDIT SYSTEM

> **Document type:** Context Preservation System (V0-P6) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Context Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Feeds:** the **Context Integrity Gate (G7)** in [`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md) and metrics **M9/M12** in [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md)
> **Complements:** the documentation audit ([`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §8 / [`../quality/DOCUMENTATION_VALIDATION.md`](../quality/DOCUMENTATION_VALIDATION.md))

This system **audits the project's memory** — it finds knowledge that is missing,
outdated, conflicting, orphaned, or undocumented, before that decay causes context
drift. Where the documentation audit checks the *docs*, the context audit checks
the *knowledge*: decisions, risks, assumptions, and their links.

> **Premise:** context rots silently. The only defense is to **look for the rot on
> a schedule** and fix it while it is cheap. A passing context audit is what makes
> deterministic recovery trustworthy.

---

## 1. The Seven Context Audits

| # | Audit | Detects | Pass criterion |
|---|-------|---------|----------------|
| **CA-1** | **Missing context** | Knowledge that exists only in a chat / PR comment / memory (a silo). | No consequential knowledge outside the repository. |
| **CA-2** | **Outdated context** | Registries/state that no longer match reality (stale `CURRENT_STATE`, overdue assumption). | Tier-3 state matches git reality; no overdue items without action. |
| **CA-3** | **Conflicting context** | Two records that disagree (two ADRs, ADR vs. doc, risk vs. decision). | Single canonical source; no contradiction; higher tier wins. |
| **CA-4** | **Orphaned knowledge** | A decision/risk/assumption/lesson/postmortem reachable by no index/link. | Every memory artifact is indexed + linked (reachable). |
| **CA-5** | **Undocumented decisions** | A consequential change with no ADR (NR-5). | 100% decision traceability (metric M8). |
| **CA-6** | **Undocumented risks** | A known hazard not in the risk register. | Every known/realized hazard registered. |
| **CA-7** | **Undocumented assumptions** | A decision resting on an unrecorded assumption; an assumption with no verification plan. | Every consequential assumption recorded with a plan (M12). |

## 2. Audit Procedures (how each is run)

- **CA-1 Missing context:** review the change set + recent work; for each
  consequential decision/result/insight, confirm it has a **repository home**
  ([`KNOWLEDGE_CAPTURE_FRAMEWORK.md`](./KNOWLEDGE_CAPTURE_FRAMEWORK.md) §3). Any
  "it's in the chat/PR" item is a finding → capture it.
- **CA-2 Outdated:** diff Tier-3 state files against git reality (current version/
  phase/work); list assumptions past their **Verification Date** and risks past
  their **review frequency**; flag superseded-but-unmarked items.
- **CA-3 Conflicting:** cross-check pairs that should agree — ADR ↔ the doc it
  governs; risk ↔ the decision handling it; lower tier ↔ higher tier. Any
  contradiction is a defect; reconcile to the canonical source (`docs/` governs).
- **CA-4 Orphaned:** from each index (Decision Registry, Active Risks, Active
  Assumptions, lessons/postmortems index) confirm every artifact is reachable and
  **bidirectionally linked**; confirm no artifact references a deleted item.
- **CA-5 Undocumented decisions:** for every consequential change in the audited
  range (changelog), confirm a corresponding ADR exists and is linked (M8 = 100%).
- **CA-6 Undocumented risks:** scan recent failures/changes/learnings for hazards
  not yet in the register; confirm realized risks have postmortems.
- **CA-7 Undocumented assumptions:** scan decisions for implicit premises; confirm
  each consequential assumption is recorded with method + date (M12).

## 3. Cadence
- **Per merge:** lightweight CA-1, CA-5, CA-7 on the change set (part of G7).
- **Per phase:** CA-2, CA-3, CA-6.
- **Per version gate / quarter / post-dormancy:** **all seven**, fully
  ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §5).

## 4. Findings → Action
Every finding is handled like any defect/failure
([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md), class **CTX**):
1. **Contain:** block the merge (G7) until captured, if in a change set.
2. **Recover:** capture the missing knowledge / reconcile the conflict / refresh the
   stale record / re-link the orphan, using git + Lore to reconstruct if needed.
3. **Record:** changelog entry; raise a **CTX** risk if systemic.
4. **Prevent:** strengthen the capture loop or recovery protocol so it cannot recur.
5. **Verify:** re-run the relevant audit; confirm M9 findings = 0.

## 5. The Determinism Guarantee
The context audit exists to keep **context recovery deterministic**: if all seven
audits pass, then following [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
reconstructs the **complete** project context — every time, with **no external
conversation required.** A failing audit is precisely a place where recovery would
have a gap; fixing it restores the guarantee.

## 6. Relationship To Other Documents
- Gate/metrics: [`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md) (G7), [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md) (M9, M12)
- Doc audit (complementary): [`../quality/DOCUMENTATION_VALIDATION.md`](../quality/DOCUMENTATION_VALIDATION.md)
- Memory systems audited: decision/risk/assumption/lesson/postmortem docs in this directory
- Recovery: [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)

Changes to this document are governance-class and require an ADR.
