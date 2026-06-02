# ADR-NNNN — <short, specific title>

> **Framework:** [`../../docs/governance/Decision_Governance.md`](../../docs/governance/Decision_Governance.md)
> **Index in:** [`../DECISION_REGISTRY.md`](../DECISION_REGISTRY.md)
> Copy this file to `.gcc/decisions/ADR-NNNN-title.md`, fill **every** field, get
> approval, then add a row to the Decision Registry and a changelog entry.

| | |
|---|---|
| **ID** | ADR-NNNN |
| **Status** | Proposed \| Accepted \| Superseded by ADR-MMMM \| Deprecated \| Rejected |
| **Date** | YYYY-MM-DD (and last status-change date) |
| **Change class** | A0 \| A1 \| A2 \| A3 \| AE (Architecture_Governance §13.1) |
| **Initiator** | <Founder \| named AI agent> |
| **Approver** | <Founder for A2+/architecture — never the producing agent (NR-7)> |
| **RFC** | RFC-NNNN (if applicable) |
| **Supersedes / Superseded by** | ADR-MMMM (if applicable) |

## Decision
<The choice made, stated in one or two unambiguous sentences.>

## Context
<The situation and forces at play; what version/phase; why this comes up now.>

## Problem
<The precise question being decided.>

## Options Considered
1. **Option A** — <description>
2. **Option B** — <description>
3. **Option C / Do nothing** — <description>
*(≥2 real options required.)*

## Tradeoffs
| Option | Pros | Cons |
|--------|------|------|
| A | | |
| B | | |
| C | | |

## Chosen Solution
<Which option, and **why it wins** under our priority order: Governance → Clinical
safety → Reproducibility → Clinical utility → Research novelty → Speed
(PROJECT_OBJECTIVES §9).>

## Consequences
<What becomes true / easier / harder. Include positive and negative.>

## Risk
<Risks introduced or accepted; link RISK-NNNN entries
([`../ACTIVE_RISKS.md`](../ACTIVE_RISKS.md)). If a shortcut/debt is accepted, link
the debt record (NR-2).>

## Future Impact
<Effect on later versions / integration points; any cross-version invariant touched
(must not be weakened).>

## Affected Systems
<Modules / contracts / invariants / docs / registries changed. Update each in the
same change set.>

## Validation
<How the decision's implementation is validated: tests, GCC checks, audits.>

## Rollback
<How this decision/change is reversed if needed (Architecture_Governance §11 for
architecture-class).>

## Review Date
<When to revisit, or "Stable / constitutional".>

## Links
<RFC, change-record/changelog entry, related ADRs, affected module READMEs.>

---
**Compliance check before `Accepted`:** every field filled · no principle/rule
violated · no invariant weakened · in scope (NR-13) · version-gate valid (NR-12) ·
rollback defined · approver is **not** the producing agent (NR-7).
