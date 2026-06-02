# RISK GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Risk Owner role)
> **Update procedure:** Governance-class change (ADR). The **live** register is [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md).
> **Enforces:** Principles **AP-8, AP-10, AP-12** and Rules **NR-2, NR-15** ([`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document defines the **risk framework**: the categories of risk the project
tracks, how each risk is scored and owned, and how risks connect to decisions,
the changelog, and the live register. The goal is that **no consequential risk is
invisible** — recorded risk is manageable; hidden risk is latent failure (the
spirit of NR-2 generalized to all risk).

---

## 1. Risk Categories

Every risk belongs to exactly one **primary** category (it may reference others).

| Code | Category | Examples |
|------|----------|----------|
| **TECH** | Technical | brittle implementation, performance cliff, flaky behavior |
| **ARCH** | Architecture | drift, cycle introduced, boundary erosion, contract breakage |
| **AI** | AI collaboration | context drift, hallucinated APIs, scope expansion, silent dependency change ([`AI_Governance.md`](./AI_Governance.md) §5) |
| **OPS** | Operational | build/release failure, environment unpinning, tooling outage |
| **CLIN** | Clinical | overconfident output, missed seizure pattern, misleading UI — *safety-relevant* |
| **SEC** | Security | data exposure, credential leak, supply-chain compromise |
| **COMP** | Compliance | auditability gaps, undocumented decisions vs. future regulatory needs |
| **CTX** | Context | lost rationale, undocumented assumption, dormancy-induced knowledge loss |
| **REPO** | Repository | entropy, orphaned/conflicting docs, dead artifacts |
| **SCALE** | Scaling | streaming/load fragility, multi-site/domain-shift fragility |

## 2. Per-Risk Specification (mandatory fields)

Every risk entry (template:
[`../../.gcc/TEMPLATES/RISK_TEMPLATE.md`](../../.gcc/TEMPLATES/RISK_TEMPLATE.md))
must define:

| Field | Meaning |
|-------|---------|
| **ID** | `RISK-NNNN` (monotonic). |
| **Title / Category** | Short title + one category from §1. |
| **Severity** | `Low / Medium / High / Critical` — impact if it occurs. |
| **Probability** | `Low / Medium / High` — likelihood within the current horizon. |
| **Impact** | What concretely breaks (which invariant/version/clinical effect). |
| **Detection** | How it is detected (GCC check, test, audit, monitoring, review). |
| **Mitigation** | What reduces probability/impact (preventive). |
| **Recovery** | What is done if it occurs (corrective; rollback/incident). |
| **Owner** | Accountable role (Founder, by category). |
| **Review Frequency** | How often it is re-evaluated (§4). |
| **Status** | `Open / Mitigating / Accepted / Closed`. |
| **Links** | ADRs, debt records, incidents, affected modules. |

## 3. Risk Scoring

**Exposure = Severity × Probability**, using the matrix:

| Severity \ Probability | Low | Medium | High |
|------------------------|-----|--------|------|
| **Critical** | High | Critical | Critical |
| **High** | Medium | High | Critical |
| **Medium** | Low | Medium | High |
| **Low** | Low | Low | Medium |

Response by exposure:
- **Critical:** stop-and-address; cannot pass a version gate while open and unmitigated.
- **High:** active mitigation with an owner and a date; reviewed every cycle.
- **Medium:** mitigation planned; reviewed each phase.
- **Low:** monitored; accepted with rationale if not mitigated.

**Any risk to a cross-version invariant or a clinical-safety property is treated as
at least High**, regardless of probability.

## 4. Review Frequency
- **Critical/High:** every active development cycle and at every version gate.
- **Medium:** at each phase boundary.
- **Low:** at each version gate.
- **All:** re-reviewed after dormancy as part of
  [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md).

## 5. Risk Workflow

```
 IDENTIFY ─► RECORD (ACTIVE_RISKS) ─► SCORE ─► ASSIGN OWNER ─► MITIGATE
      ▲                                                          │
      │                                                          ▼
   re-review ◄──────────────── MONITOR ◄──────── (occurs?) ─► RECOVER + POSTMORTEM
```

- New risks are added to [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md).
- A realized risk triggers **Recovery** + an **incident/postmortem**
  ([`Release_Governance.md`](./Release_Governance.md) §8) captured as Lore.
- A risk that motivates a decision is linked to its **ADR**.
- **Accepted** risks require a recorded rationale (and, if they imply a shortcut, a
  debt record — NR-2).

## 6. Integration With The Governance Framework
- **Decisions:** risks are referenced by ADRs ([`Decision_Governance.md`](./Decision_Governance.md)).
- **Change/Review:** every A2+ change records its risk classification
  (Architecture_Governance §13.1) and registers introduced risk.
- **AI:** the AI failure modes ([`AI_Governance.md`](./AI_Governance.md) §5) are
  pre-seeded **AI**-category risks in the live register.
- **Testing/Monitoring:** detection mechanisms for many risks are tests
  ([`Testing_Governance.md`](./Testing_Governance.md)) and monitoring/drift
  signals (AP-10, NR-15).

## 7. Risk Register Template
A blank register row and full entry template are in
[`../../.gcc/TEMPLATES/RISK_TEMPLATE.md`](../../.gcc/TEMPLATES/RISK_TEMPLATE.md);
the live register lives at [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md).

## 8. Relationship To Other Governance Documents
- Decisions: [`Decision_Governance.md`](./Decision_Governance.md) · Change: [`Change_Management.md`](./Change_Management.md)
- Release/Incident: [`Release_Governance.md`](./Release_Governance.md) · AI: [`AI_Governance.md`](./AI_Governance.md)
- Live register: [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md) · Assumptions: [`../../.gcc/ACTIVE_ASSUMPTIONS.md`](../../.gcc/ACTIVE_ASSUMPTIONS.md)

Changes to this document are governance-class and require an ADR.
