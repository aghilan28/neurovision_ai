# RFC-NNNN — <title>

> **Framework:** [`../../docs/governance/RFC_Process.md`](../../docs/governance/RFC_Process.md)
> Copy to `.gcc/rfcs/RFC-NNNN-title.md`, fill every section, route through the RFC
> lifecycle (Proposal → Review → Discussion → Approval → Implementation →
> Validation → Closure). Approval produces an ADR.

| | |
|---|---|
| **ID** | RFC-NNNN |
| **Title** | <title> |
| **Author** | <Founder \| named AI agent> |
| **Date** | YYYY-MM-DD |
| **Status** | Draft \| Under-Review \| Discussion \| Accepted \| Rejected \| Implemented \| Closed \| Withdrawn |
| **Target version/phase** | <e.g. V1 / V1-preprocessing> |
| **Resulting ADR** | ADR-NNNN (once decided) |

## Summary
<One paragraph: what this proposes.>

## Motivation / Problem
<Why now; what breaks or is blocked if we do nothing.>

## Scope & Version Check
- In scope? <yes + reference PROJECT_SCOPE item> (NR-13)
- Version-gate valid? <yes + which prerequisites are met> (NR-12)

## Proposed Change
<The precise structural/behavioral change. Be concrete.>

## Impact
- **Modules touched:** <…>
- **Contracts affected:** <…>
- **Invariants:** <list each potentially-affected invariant and argue none is weakened>
- **Dependency graph:** <any new/changed edge? if yes, this is A3>
- **Docs/registries to update:** <…>

## Options & Tradeoffs
| Option | Pros | Cons |
|--------|------|------|
| Proposed | | |
| Alternative 1 | | |
| Do nothing | | |
*(≥2 real alternatives, including "do nothing".)*

## Risks
<List with categories; link/seed RISK-NNNN entries
([`../../docs/governance/Risk_Governance.md`](../../docs/governance/Risk_Governance.md)).>

## Rollback Plan
<How the change is reversed.>

## Validation Plan
<What tests/GCC checks/audits prove it correct (Testing_Governance).>

## Open Questions / Assumptions
<Explicit unknowns; record consequential assumptions in
[`../ACTIVE_ASSUMPTIONS.md`](../ACTIVE_ASSUMPTIONS.md).>

## Recommendation
<Clear recommendation the approver can accept/reject.>

---
**Quality bar (RFC_Process §4):** real alternatives · honest tradeoffs · every
invariant considered · concrete rollback + validation · self-contained · ends in a
clear recommendation.
