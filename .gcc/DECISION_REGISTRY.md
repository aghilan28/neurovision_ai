# DECISION REGISTRY — Master ADR Index

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — the authoritative index of every Architecture/Any Decision Record (ADR).
> **Owner:** Founder · **Kept current by:** the active contributor
> **Framework:** [`../docs/governance/Decision_Governance.md`](../docs/governance/Decision_Governance.md) · **Template:** [`TEMPLATES/ADR_TEMPLATE.md`](./TEMPLATES/ADR_TEMPLATE.md)
> **Update procedure:** Add a row when an ADR is created; update status on lifecycle change (append-only — never delete). Log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P4

This registry links **every decision** to its rationale, alternatives,
consequences, and affected systems. It is how a future agent answers *"why is this
the way it is?"* deterministically. ADRs are **append-only**: superseded decisions
are marked, never erased (Rule **NR-14**, Principle **AP-9**).

> **Storage:** Full ADR documents live under `.gcc/decisions/ADR-NNNN-*.md`
> (created as decisions are made, using the template). This file is the **index**.

---

## How to add a decision
1. Draft from [`TEMPLATES/ADR_TEMPLATE.md`](./TEMPLATES/ADR_TEMPLATE.md) (often from
   an RFC — [`../docs/governance/RFC_Process.md`](../docs/governance/RFC_Process.md)).
2. Get approval per [`../docs/governance/Decision_Governance.md`](../docs/governance/Decision_Governance.md)
   (**Founder** for A2+/architecture; **never** AI self-approval — NR-7).
3. Save as `.gcc/decisions/ADR-NNNN-title.md`; add a row below; link it from the
   artifacts it governs; add a changelog entry.

## Index

| ID | Title | Status | Date | Class | Affected systems | Links |
|----|-------|--------|------|-------|------------------|-------|
| ADR-0000 | Decision-registry initialized (this index) | Accepted | V0-P4 | Governance | `.gcc/` | Decision_Governance |
| *ADR-0001+* | *(first project decisions recorded as work begins)* | — | — | — | — | — |

> The constitution's foundational choices (patient-disjoint validation,
> uncertainty-aware inference, deterministic preprocessing, governance-by-construction,
> no-rewrite) are **already authoritative** in `docs/` (AP-1…AP-12 / NR-1…NR-15).
> They are treated as **accepted constitutional baselines**; a canonical ADR-shaped
> example (LOSO) is shown in
> [`../docs/governance/Decision_Governance.md`](../docs/governance/Decision_Governance.md) §6.
> Future ADRs that touch them must reference and not weaken them.

## Decision Backlog (anticipated ADRs, to be drafted via RFC before V1 work)
| Provisional | Topic | Trigger |
|-------------|-------|---------|
| (RFC→ADR) | V0 exit-gate completion record | End of V0 (NR-12). |
| (RFC→ADR) | GCC automation approach (how checks are implemented in CI) | Before substantial V1 code. |
| (RFC→ADR) | Preprocessing strategy & determinism approach | V1 start (AP-3). |
| (RFC→ADR) | Patient-disjoint split strategy specifics | V1 start (AP-2). |
| (RFC→ADR) | UQ technique selection (Conformal vs. alternatives) | V1 modeling (AP-4; ASM-0003). |
| (RFC→ADR) | Model family selection (e.g. Mamba-class vs. alternatives) | V1 modeling (ASM-0004). |

## Status legend
`Proposed` · `Accepted` · `Superseded by ADR-MMMM` · `Deprecated` · `Rejected`
(rejected/superseded entries remain in the index permanently).

## Registry Hygiene
- IDs are monotonic and zero-padded (`ADR-NNNN`); never reused.
- Every architecture/governance/major change has a corresponding ADR (NR-5).
- Every ADR row links to its document and to the change/RFC/risks it relates to.
- A decision that changes a definition or term also updates the Glossary (NR-14).
