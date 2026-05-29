# V0 EXIT CRITERIA

> **Document type:** Version 0 Certification (V0-P8) · **Tier 2**
> **Status:** Authoritative — **measurable** mandatory requirements
> **Owner:** Founder (Certification Authority)
> **Update procedure:** Governance-class change (ADR).
> **Source:** [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §1 (V0 exit criteria) + the V0-P1…P8 deliverables
> **Evaluated by:** the audits ([`V0_AUDIT_FRAMEWORK.md`](./V0_AUDIT_FRAMEWORK.md)) and the P8 evidence run

The **mandatory, measurable** requirements V0 must meet to certify. Each is binary
(MET / NOT MET) with an objective check. **All mandatory criteria must be MET** for
any PASS outcome; clinical-safety/validation-integrity criteria are **never
waivable**.

---

## 1. Mandatory Exit Criteria (each measurable)

| # | Criterion | Measure (objective) | Status |
|---|-----------|---------------------|--------|
| **EC-1** | **Architecture approved** | 5 architecture docs present; graph acyclic; import rules explicit; **0 stray AP/NR IDs**; registry reconciled | ✅ MET |
| **EC-2** | **Governance approved** | 10 governance docs + index; change router + ADR + risk frameworks present & consistent | ✅ MET |
| **EC-3** | **Context approved** | 10 context docs + index; 13 `.gcc/` memory artifacts present + carry "Last updated"; CA-1…CA-7 pass; recovery deterministic | ✅ MET |
| **EC-4** | **Quality approved** | 11 quality docs + index; gates G1–G8 defined; metrics M1–M12 + hard-zeros defined | ✅ MET |
| **EC-5** | **Environment approved** | 12 environment docs + index; 6 workflows present + logic verified; bootstrap + onboarding deterministic | ✅ MET (CI host-observation = V1-entry condition) |
| **EC-6** | **Documentation approved** | **0 broken internal links**; **0 placeholders** in authoritative docs; every doc declares Owner + Update procedure; navigable from root | ✅ MET |
| **EC-7** | **AI workflows approved** | Approved AI systems + workflows; AI onboarding hard gate; AI output validation + AI-TRACE defined | ✅ MET (cold-onboarding empirical test = V1-entry condition) |
| **EC-8** | **Repository health approved** | Every required directory has a governance README; repository-health checks green; no hard-zero metric breached | ✅ MET |
| **EC-9** | **No open Critical risk** | [`V0_RISK_REVIEW.md`](./V0_RISK_REVIEW.md): open Critical = **0** | ✅ MET |
| **EC-10** | **No Blocker/Major gap** | [`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md): Blocker = 0, Major = 0 | ✅ MET |
| **EC-11** | **No version-skip** | All prior phases (P1–P7) complete and recorded; V0 is the first version (no prior to skip) — NR-12 | ✅ MET |
| **EC-12** | **V0-completion ADR recorded** | An accepted ADR records the certification outcome in [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) | ✅ MET (ADR-0001) |

## 2. Measurement Method
Criteria are evaluated by the **re-runnable** checks behind the CI workflows
([`../../.github/workflows/`](../../.github/workflows/)) and the P8 evidence run
recorded in [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md) §evidence. Each
"✅ MET" is backed by that evidence; conditions (where noted) are non-Critical and
scheduled at V1 entry — they do **not** flip a criterion to NOT MET because the V0
deliverable (the *capability/specification*) is present; only its *empirical
host-confirmation* is pending.

## 3. Waivability
- **Never waivable:** EC-9 (no Critical risk), EC-10 (no Blocker/Major gap), EC-11
  (no version-skip), and any clinical-safety/validation-integrity element.
- **Condition-eligible:** EC-5/EC-7 empirical confirmations (host CI observed; cold
  onboarding run) — permitted as **CERTIFIED WITH CONDITIONS** because each is
  non-Critical, owned, and scheduled, and the underlying capability is present.

## 4. Result
**All 12 mandatory exit criteria are MET** (EC-5 and EC-7 carry non-Critical,
scheduled conditions). Combined with **0 Critical risks** and **0 Blocker/Major
gaps**, V0 satisfies its exit criteria → outcome **CERTIFIED WITH CONDITIONS**
([`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md)).

## 5. Relationship To Other Documents
- Readiness/audit/risk/gap: the other documents in this directory.
- Version gate: [`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md), [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md)
- V1 entry: [`V1_READINESS_GATE.md`](./V1_READINESS_GATE.md)

Changes to this document are governance-class and require an ADR.
