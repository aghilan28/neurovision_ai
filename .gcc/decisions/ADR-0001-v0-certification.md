# ADR-0001 — Version 0 certified complete (with conditions); authorize Version 1 entry

> **Framework:** [`../../docs/governance/Decision_Governance.md`](../../docs/governance/Decision_Governance.md)
> **Index in:** [`../DECISION_REGISTRY.md`](../DECISION_REGISTRY.md)

| | |
|---|---|
| **ID** | ADR-0001 |
| **Status** | Accepted |
| **Date** | V0-P8 |
| **Change class** | A3 (governance / version-gate) |
| **Initiator** | Founder (with AI agent drafting under AI_Governance) |
| **Approver** | **Founder** (Certification Authority; NR-7 — not the producing agent) |
| **RFC** | V0-P8 certification (this directive) |
| **Supersedes / Superseded by** | — |

## Decision
**Version 0 (Repository Foundation) is CERTIFIED COMPLETE — with conditions.**
Version 1 (Offline EEG Platform) is **authorized to begin** under the conditions in
[`../../docs/certification/V1_READINESS_GATE.md`](../../docs/certification/V1_READINESS_GATE.md).

## Context
V0 spanned eight phases (P1–P8) building the constitution, architecture, governance,
AI OS, quality, context, environment, and certification. NR-12 forbids starting V1
until V0's exit criteria are met and recorded. P8 performed a genuine, evidence-backed
certification (audits, scored readiness, risk review, gap analysis).

## Problem
Is the V0 foundation genuinely sound enough to safely support V1–V4, and may V1 begin?

## Options Considered
1. **Certify complete (unconditional).**
2. **Certify complete with conditions** (non-Critical items scheduled at V1 entry).
3. **Defer** until every empirical confirmation (CI observed; cold onboarding) is done.
4. **Block** (treat conditions as blockers).

## Tradeoffs
| Option | Pros | Cons |
|--------|------|------|
| 1 | Clean | **Dishonest** — CI not yet observed on host; cold onboarding not run. |
| 2 | Honest; unblocks V1; tracks residuals | Carries named, owned conditions. |
| 3 | Maximally cautious | Conditions are *V1-entry* tasks; deferring all of V0 for them is disproportionate (no Critical blocker). |
| 4 | — | Wrong: no Blocker/Major gap and 0 Critical risks exist. |

## Chosen Solution
**Option 2 — CERTIFIED WITH CONDITIONS.** All 12 mandatory exit criteria are MET; 0
open Critical risks; 0 Blocker/Major gaps. The two residual conditions (observe CI
green on the first V1 PR; run a cold-onboarding test) are **non-Critical**, owned by
the Founder, and **must close before the first V1 code merges to `main`** — they do
not block starting V1. This is the honest outcome under the certification standard
(evidence over assertion).

## Consequences
- V0 is the **permanent, certified foundation**; V1 may begin (gated).
- The conditions become V1-entry tasks ([`V1_READINESS_GATE.md`](../../docs/certification/V1_READINESS_GATE.md) §1).
- The completion report ([`../../docs/certification/V0_COMPLETION_REPORT.md`](../../docs/certification/V0_COMPLETION_REPORT.md)) is the permanent record.

## Risk
Residual: CI host-behavior unknown (ASM-0006) and cold-onboarding effectiveness
unknown (ASM-0001) — both **non-Critical**, mitigated by scheduling at V1 entry. No
Critical risk is open ([`../../docs/certification/V0_RISK_REVIEW.md`](../../docs/certification/V0_RISK_REVIEW.md)).

## Future Impact
Binds the V0→V1 transition; any later finding that certification rested on faulty
evidence triggers a postmortem + re-certification.

## Affected Systems
The whole repository (certification is repo-wide); live state files updated
(`CURRENT_STATE`, `VERSION_STATUS`, `NEXT_STATE`); the Decision Registry.

## Validation
The P8 evidence run (audits): 0 broken links, 0 placeholders, 0 stray AP/NR IDs,
complete ownership, all phase artifacts present + consistent, 6 workflows verified.

## Rollback
If a Blocker is later discovered: set V0 status back to "in certification," open a
postmortem, halt V1 code merges, remediate, re-certify (a new dated report + ADR).

## Review Date
At the close of the V1-entry conditions (confirm CI green + cold-onboarding), and at
the V1→V2 gate.

## Links
[`V0_COMPLETION_REPORT.md`](../../docs/certification/V0_COMPLETION_REPORT.md) ·
[`V0_EXIT_CRITERIA.md`](../../docs/certification/V0_EXIT_CRITERIA.md) ·
[`V0_READINESS_ASSESSMENT.md`](../../docs/certification/V0_READINESS_ASSESSMENT.md) ·
[`V1_READINESS_GATE.md`](../../docs/certification/V1_READINESS_GATE.md) · ASM-0001, ASM-0006; RISK-0003.
