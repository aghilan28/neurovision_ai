# ASM-NNNN — <short title>

> **Register in:** [`../ACTIVE_ASSUMPTIONS.md`](../ACTIVE_ASSUMPTIONS.md)
> **Why:** unrecorded assumptions silently become "facts" → context drift (NR-14).
> Every consequential assumption is recorded with a verification plan.

| Field | Value |
|-------|-------|
| **ID** | ASM-NNNN |
| **Assumption** | <the thing being treated as true without verification> |
| **Confidence** | Low \| Medium \| High |
| **Status** | Open \| Verified \| Refuted \| Retired |
| **Owner** | <Founder> |

## Evidence
<What (if anything) currently supports this assumption.>

## Verification Plan
<How and when this will be confirmed or refuted. An assumption with no plan is a
defect.>

## Impact if Wrong
<What breaks if the assumption is false — and whether this also warrants a RISK
entry (high-impact + low-confidence ⇒ also register a risk).>

## Links
<Related ADRs, risks, modules, RFCs.>

---
**On resolution:** mark `Verified`/`Refuted`/`Retired` (do not delete — append-only);
link the decision (ADR) that resolved it. A refuted assumption that changes a
decision triggers an ADR.
