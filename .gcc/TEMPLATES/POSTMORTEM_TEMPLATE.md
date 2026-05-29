# Postmortem — <incident title>

> **Framework:** [`../../docs/governance/Release_Governance.md`](../../docs/governance/Release_Governance.md) §8 + [`../LORE_PROTOCOL.md`](../LORE_PROTOCOL.md) §7
> Copy to `.gcc/postmortems/PM-NNNN-title.md`. Postmortems are **blameless and
> durable** — the goal is to prevent recurrence, not to assign fault.

| | |
|---|---|
| **ID** | PM-NNNN |
| **Date** | YYYY-MM-DD |
| **Author** | <Founder \| agent> |
| **Severity** | Low \| Medium \| High \| Critical |
| **Status** | Draft \| Final |

## Summary
<One paragraph: what happened and the impact.>

## Timeline
<Chronological sequence: detection → diagnosis → mitigation → resolution (with times).>

## Impact
<What/who was affected; which invariant or guarantee was at risk; any clinical-safety
relevance.>

## Root Cause(s)
<The actual cause(s), not just symptoms. Use "why" repeatedly.>

## What Caught It / What Didn't
<Which check, test, monitor, or review detected it — or why it was missed
(detection gap).>

## Corrective Actions (now)
<What was done to resolve the immediate problem; rollback used?>

## Preventive Actions (future)
<New/strengthened check, test, rule, or doc so this **cannot recur silently**.
Each action links to a follow-up change.>

## Follow-ups
<Links to new RISK-NNNN, ADR-NNNN, tests, and change records created.>

## Lessons (Lore)
<Durable learnings to carry forward; reflect in
[`../learnings/`](../LORE_PROTOCOL.md) and, if shared understanding changes, the
Glossary.>

---
**Outcome:** every postmortem yields at least one **prevention** (a new test/check/
rule). An incident with no preventive action is not closed.
