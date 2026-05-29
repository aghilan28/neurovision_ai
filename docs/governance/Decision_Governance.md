# DECISION GOVERNANCE (ADR FRAMEWORK)

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Decision Owner role)
> **Update procedure:** Governance-class change (ADR — recursively, a change here is itself recorded).
> **Enforces:** Principles **AP-9, AP-11, AP-12** and Rules **NR-5, NR-14** ([`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document defines the **Architecture/Any Decision Record (ADR)** framework —
how consequential decisions are made, recorded, indexed, and preserved. ADRs are
the mechanism that makes **AP-9 (Versioned Decisions)** real and that defends
against **context drift**: code shows *what*, ADRs preserve *why*. Every ADR is
indexed in the **Decision Registry**
([`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md)).

> **Core rule (NR-5):** no consequential or architectural change may proceed
> without a recorded, reviewed decision.

---

## 1. What Requires an ADR

An ADR is **required** for any decision that is consequential and not easily
reversible, including:
- any **architecture-class** change (Architecture_Governance §2);
- any new/changed **external dependency** other modules rely on;
- any **method choice** with downstream impact (model family, UQ technique,
  evaluation design, preprocessing strategy);
- any **governance** change (to a `docs/governance/*` or constitution document);
- any **scope** promotion (FUTURE → IN) or version-gate decision;
- any **accepted technical debt** (paired with a debt record, NR-2);
- any decision that **supersedes** a prior ADR.

An ADR is **not** required for routine, reversible, in-boundary implementation
that changes no contract or invariant (those follow the lighter paths in
[`Change_Management.md`](./Change_Management.md)) — but **when in doubt, record it**.

## 2. ADR — Mandatory Fields

Every ADR **must** contain all of the following (template:
[`../../.gcc/TEMPLATES/ADR_TEMPLATE.md`](../../.gcc/TEMPLATES/ADR_TEMPLATE.md)):

| Field | Meaning |
|-------|---------|
| **ID** | `ADR-NNNN` (zero-padded, monotonic). |
| **Title** | Short, specific. |
| **Status** | `Proposed` → `Accepted` → (`Superseded by ADR-MMMM` / `Deprecated`). Append-only. |
| **Date** | Decision date (and last-status-change date). |
| **Owner / Approver** | Proposer and the approver (**Founder** for A2+/architecture). |
| **Decision** | The choice made, stated unambiguously. |
| **Context** | The situation and forces at play. |
| **Problem** | The precise question being decided. |
| **Options** | The real alternatives considered (≥2; "do nothing" counts). |
| **Tradeoffs** | Pros/cons of each option. |
| **Chosen Solution** | Which option and **why** it wins under our priorities. |
| **Consequences** | What becomes true/easier/harder as a result. |
| **Risk** | Risks introduced/accepted; linked `RISK-` ids ([`Risk_Governance.md`](./Risk_Governance.md)). |
| **Future Impact** | Effect on later versions/integration points. |
| **Review Date** | When this decision should be revisited (or "stable"). |
| **Affected Systems** | Modules/contracts/invariants/docs touched. |
| **Links** | RFC, change record, registry entry, related ADRs. |

An ADR missing any mandatory field is **not valid** and cannot gate a change.

## 3. Decision Lifecycle

```
 PROPOSED ──review──► ACCEPTED ──(time/new evidence)──► SUPERSEDED (by a new ADR)
     │                                                         ▲
     └────────────────── REJECTED (recorded, kept) ───────────┘
```

- **Proposed:** drafted (often from an RFC — [`RFC_Process.md`](./RFC_Process.md));
  not yet authoritative.
- **Accepted:** approved by the required approver; now governs.
- **Superseded/Deprecated:** replaced by a newer ADR; **never deleted** — the
  record and its rationale are permanent Lore (NR-14).
- **Rejected:** recorded with the reason, so the option is not silently re-tried.

**Append-only principle:** ADRs are never edited to erase history. Corrections are
new ADRs (or explicitly marked status changes) that link to what they change.

## 4. Approval Process

| Decision class | Approver |
|----------------|----------|
| A0/A1 minor (rarely needs an ADR) | Reviewer |
| A2 major (contract/dependency/method) | **Founder** |
| A3 architecture / invariant / governance / scope / version-gate | **Founder (mandatory)** |
| Emergency (AE) | **Founder** — retroactive ADR within **72 hours** |

No AI agent approves an ADR (NR-7); an agent may **draft** it. Approval is
recorded in the ADR (`Status: Accepted`, approver, date) and indexed in the
Decision Registry.

## 5. Indexing & Traceability
- Every ADR is listed in [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md)
  with its id, title, status, date, and links to rationale/alternatives/
  consequences/affected systems.
- ADRs are linked **from the artifacts they govern** (architecture docs, module
  READMEs, dependency/risk registries) and **to** the RFC and changelog entry that
  produced them.
- This bidirectional linking is what lets a future agent answer "why is this the
  way it is?" deterministically (the recovery target of
  [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)).

## 6. Worked Example (illustrative)

> **ADR-0001 — Adopt patient-disjoint (LOSO) evaluation as the only valid regime**
> *(This decision is already fixed by the constitution — AP-2/NR-3 — and is shown
> here as a canonical example of ADR shape; it is recorded as `Accepted` in the
> registry as the baseline rationale.)*
> - **Status:** Accepted · **Date:** V0 · **Approver:** Founder
> - **Decision:** All evaluation splits are patient-disjoint; LOSO is default.
> - **Context:** ICU EEG has high inter-patient variability; leaked splits inflate metrics.
> - **Problem:** Which evaluation regime yields clinically trustworthy metrics?
> - **Options:** (a) random segment split; (b) recording-level split; (c) patient-disjoint/LOSO.
> - **Tradeoffs:** (a)/(b) easier, higher apparent accuracy, but leak patient identity; (c) harder, lower apparent accuracy, but honest.
> - **Chosen Solution:** (c) — only (c) measures performance on unseen patients, the only clinically meaningful target.
> - **Consequences:** Lower headline numbers; defensible results; enforced by `evaluation/` + tests + GCC.
> - **Risk:** None vs. the alternatives' leakage risk; mislabeled "low accuracy" perception → mitigate via documentation.
> - **Future Impact:** Binds V1–V4; streaming (V3) must preserve disjointness.
> - **Review Date:** Stable (constitutional).
> - **Affected Systems:** `evaluation/`, `datasets/`, `tests/`, GCC.

A blank, fillable version is in
[`../../.gcc/TEMPLATES/ADR_TEMPLATE.md`](../../.gcc/TEMPLATES/ADR_TEMPLATE.md).

## 7. Relationship To Other Governance Documents
- Proposals: [`RFC_Process.md`](./RFC_Process.md) · Change paths: [`Change_Management.md`](./Change_Management.md)
- Architecture: [`Architecture_Governance.md`](./Architecture_Governance.md) · Risk: [`Risk_Governance.md`](./Risk_Governance.md)
- Registry: [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) · Lore: [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md)

Changes to this document are governance-class and require an ADR.
