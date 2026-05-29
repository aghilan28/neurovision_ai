# RISK-NNNN — <short title>

> **Framework:** [`../../docs/governance/Risk_Governance.md`](../../docs/governance/Risk_Governance.md)
> **Register in:** [`../ACTIVE_RISKS.md`](../ACTIVE_RISKS.md)
> Fill every field. Any risk to a cross-version invariant or clinical-safety
> property is treated as **≥ High** regardless of probability.

| Field | Value |
|-------|-------|
| **ID** | RISK-NNNN |
| **Title** | <short title> |
| **Category** | TECH \| ARCH \| AI \| OPS \| CLIN \| SEC \| COMP \| CTX \| REPO \| SCALE |
| **Severity** | Low \| Medium \| High \| Critical |
| **Probability** | Low \| Medium \| High |
| **Exposure** | (Severity × Probability — Risk_Governance §3 matrix) |
| **Status** | Open \| Mitigating \| Accepted \| Closed |
| **Owner** | <Founder, by category> |
| **Review frequency** | every cycle \| each phase \| each gate |

## Impact
<What concretely breaks — which invariant/version/clinical effect.>

## Detection
<How it is detected: GCC check, test, audit, monitoring, review.>

## Mitigation (preventive)
<What reduces probability/impact.>

## Recovery (corrective)
<What is done if it occurs: rollback / incident / postmortem.>

## Links
<ADRs, debt records, incidents, affected modules, related risks.>

---
**Register row form** (for [`../ACTIVE_RISKS.md`](../ACTIVE_RISKS.md)):
`RISK-NNNN · <category> · Sev/Prob=Exposure · <title> · Status · Owner`

**If Accepted:** record the rationale (and a debt record if it implies a shortcut —
NR-2). **Critical/High open risks block a version gate** (Risk_Governance §3).
