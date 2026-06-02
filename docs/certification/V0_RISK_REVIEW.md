# V0 RISK REVIEW

> **Document type:** Version 0 Certification (V0-P8) · **Tier 2**
> **Status:** Authoritative — **formal risk assessment** at the V0 gate
> **Owner:** Founder (Certification Authority / Risk Owner)
> **Update procedure:** Governance-class change (ADR); risks themselves live in [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md).
> **Framework:** [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) · **Memory:** [`../context/RISK_MEMORY_SYSTEM.md`](../context/RISK_MEMORY_SYSTEM.md)

A formal review of the risk posture **at the V0 → V1 gate.** The certifying
question is narrow and decisive: **is any risk a Critical blocker to starting V1?**
(Exposure scoring per Risk_Governance §3; any risk to a cross-version invariant or
clinical-safety property is treated **≥ High**.)

> **Gate rule:** **no open Critical risk** may exist for V0 to certify
> ([`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md)). High risks must have an owner +
> mitigation; they do not, by themselves, block certification.

---

## 1. Open Risks (active; live: [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md))

| ID | Category | Severity × Prob = Exposure | Status | Blocker? | Mitigation |
|----|----------|----------------------------|--------|----------|------------|
| **RISK-0001** | CTX | High × High = **Critical-exposure** | Mitigating | **No** | The entire AI OS + Lore + deterministic recovery; this is the risk V0 was built to control. Residual is managed, not open-Critical-unmitigated. |
| **RISK-0002** | AI | High × Med = High | Mitigating | No | AI governance + AI output validation (trust/confidence/risk) + mandatory human review (NR-7) + AI-TRACE. |
| **RISK-0003** | ARCH | High × Med = High | **Reduced** | No | **P7 closed the automation gap**: `architecture.yml` + boundary checks now mechanize drift detection (was the main open item last phase). |
| **RISK-0004** | REPO | Med × Med = Med | Mitigating | No | Documentation gate + repository-health workflow + six doc scans. |
| **RISK-0005** | CLIN | Critical × Low = High | Open (watch) | No | Anticipated, activates V1 when models exist; uncertainty + abstention by construction. No clinical output exists in V0. |
| **RISK-0006** | OPS/ARCH | High × Low = Med | Open (watch) | No | Version-gate enforcement (NR-12) at classification + gates. |

**No risk is open-Critical-unmitigated.** RISK-0001's *inherent* exposure is the
highest, but it is **the risk the entire V0 foundation mitigates by design**, and
its residual is managed (recovery is deterministic; memory is append-only).

## 2. Resolved / Reduced Risks
- **RISK-0003 (architecture drift before automation)** — materially **reduced** this
  phase: the CI workflows (`architecture`, `documentation`, `context`,
  `repository-health`) now mechanize the checks that were previously manual. It moves
  from "Open (manual only)" toward "Mitigating (automated)"; final closure when CI is
  **observed** green on the host (a V1-entry condition, not a blocker).

## 3. Unknown / Emerging Risks (named, with reduction plans)
Per [`../context/RISK_MEMORY_SYSTEM.md`](./V0_RISK_REVIEW.md) §4 discipline (naming
ignorance):
- **CI host behavior unknown** until first observed run (reduction: confirm green on
  the first V1 PR — ASM-0006).
- **Cold-onboarding effectiveness unknown** until a fresh agent runs it end-to-end
  (reduction: a cold-onboarding test at V1 entry — ASM-0001).
- **Real EEG data characteristics unknown** until V1 (reduction: verify ASM-0002/0003/
  0004 against actual data; *no model adopted without patient-disjoint evidence*).

## 4. Future Risks (deferred to their version)
- **CLIN** overconfidence (V1+ when models exist) — RISK-0005.
- **SCALE** streaming/load fragility (V3+).
- **SEC** clinical-data + deployment secrets (V1+ data access; V4 deployment).
These are **out of V0 scope** to *occur*, but are pre-recorded so they are not a
surprise.

## 5. Risk by Certification Dimension
| Dimension | Dominant risk | Net effect on certification |
|-----------|---------------|-----------------------------|
| Architecture | RISK-0003 (reduced) | None (mitigated + automated) |
| AI | RISK-0002 | Condition (cold test) — non-blocking |
| Environment | CI-host unknown | Condition (observe CI) — non-blocking |
| Context | RISK-0001 | Mitigated by design — non-blocking |
| Repository | RISK-0004 | None (gated) |
| Version | RISK-0006 | None (NR-12 enforced) |

## 6. Formal Risk Verdict
- **Open Critical risks: 0.**
- **High risks: present, all owned + mitigated** (RISK-0001/0002/0005), none a V1-start
  blocker.
- **Net:** the risk posture **permits certification** (CERTIFIED WITH CONDITIONS).
  The conditions map to the unknown-risk reduction plans (§3) and are scheduled at V1
  entry ([`V1_READINESS_GATE.md`](./V1_READINESS_GATE.md)).

## 7. Relationship To Other Documents
- Live register/framework: [`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md), [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md)
- Gaps/readiness/exit: [`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md), [`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md), [`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md)

Changes to this document are governance-class and require an ADR.
