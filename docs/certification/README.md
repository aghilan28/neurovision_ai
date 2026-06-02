# `docs/certification/` — Version 0 Certification Index (V0-P8)

> **Document type:** Version 0 Certification (V0-P8) index · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Certification Authority)
> **Update procedure:** Index updated (Documentation change) when a certification doc is added; the certification *record* is append-only (ADR-0001).
> **Parent:** [`../README.md`](../README.md)

The **Version 0 Certification** — the formal, evidence-backed proof that V0 is
complete and the transition into V1. P8 **builds nothing; it audits everything.**
**Version 1 may not begin until certification succeeds** (NR-12).

> **Outcome:** **CERTIFIED WITH CONDITIONS** — see [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md) (recorded as ADR-0001).

---

## Documents

| Document | Role |
|----------|------|
| [`V0_CERTIFICATION_STANDARD.md`](./V0_CERTIFICATION_STANDARD.md) | Philosophy, authority, workflow, evidence, outcomes, escalation, expiration. |
| [`V0_AUDIT_FRAMEWORK.md`](./V0_AUDIT_FRAMEWORK.md) | 8 audit categories + procedures + checklists + evidence requirements. |
| [`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md) | 8 scored dimensions + evidence model + pass/fail (overall ~94, READY WITH CONDITIONS). |
| [`V0_RISK_REVIEW.md`](./V0_RISK_REVIEW.md) | Formal risk assessment at the gate (open Critical = 0). |
| [`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md) | Findings + severity (0 Blocker/Major) + remediation framework. |
| [`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md) | 12 measurable mandatory criteria (all MET). |
| [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md) | **Permanent record** + certification outcome. |
| [`V1_READINESS_GATE.md`](./V1_READINESS_GATE.md) | Conditions / forbidden shortcuts / required artifacts to enter V1. |

## How certification fits together
```
            V0_CERTIFICATION_STANDARD  (how we certify; outcomes)
                       │
                       ▼
            V0_AUDIT_FRAMEWORK  (AUD-ARCH/GOV/QUAL/CTX/ENV/REPO/AI/DOC)
                       │ produces evidence for
        ┌──────────────┼───────────────┬───────────────────┐
        ▼              ▼               ▼                    ▼
 V0_READINESS_     V0_RISK_REVIEW   V0_GAP_ANALYSIS    V0_EXIT_CRITERIA
 ASSESSMENT        (Critical=0)     (Blocker/Major=0)  (12/12 MET)
        └──────────────┴───────────────┴───────────────────┘
                       │ combined into
              V0_COMPLETION_REPORT  (OUTCOME: CERTIFIED WITH CONDITIONS; ADR-0001)
                       │ opens
              V1_READINESS_GATE  (conditions to enter V1; NR-12)
```

## Reading order
1. [`V0_CERTIFICATION_STANDARD.md`](./V0_CERTIFICATION_STANDARD.md)
2. [`V0_AUDIT_FRAMEWORK.md`](./V0_AUDIT_FRAMEWORK.md)
3. [`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md) → [`V0_RISK_REVIEW.md`](./V0_RISK_REVIEW.md) → [`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md)
4. [`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md)
5. [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md) → [`V1_READINESS_GATE.md`](./V1_READINESS_GATE.md)

All changes to documents in this directory are **governance-class** and require an
ADR; the certification record itself is **append-only** (never deleted).
