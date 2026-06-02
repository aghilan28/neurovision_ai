# V0 CERTIFICATION STANDARD

> **Document type:** Version 0 Certification (V0-P8) · **Tier 2 (process authority)**
> **Status:** Authoritative
> **Owner:** Founder (Certification Authority)
> **Update procedure:** Governance-class change (ADR — [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
> **Enforces:** Rule **NR-12** (no version skip); the version-gate procedure ([`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md), [`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This is the standard by which **Version 0 is certified complete.** P8 **builds
nothing** — it **audits everything** and produces a formal, evidence-backed verdict.
**Version 1 may not begin until certification succeeds** (NR-12).

> **Premise:** certification is *earned by evidence*, never granted by assertion or
> by reaching the end of a checklist. A foundation that cannot prove it is sound is
> not certified — it is, at best, deferred.

---

## 1. Certification Philosophy
- **Evidence over assertion.** Every claim of completeness is backed by a re-runnable
  check or a linked artifact ([`V0_AUDIT_FRAMEWORK.md`](./V0_AUDIT_FRAMEWORK.md)).
- **Honest over convenient.** If a control is missing or unproven, it is recorded as
  a gap/risk — not glossed (the directive forbids superficial audits).
- **Foundation-fit, not feature-complete.** V0's job is to make V1–V4 *safe to
  build*; certification measures **that**, not the presence of application features
  (there is intentionally no code in V0).
- **Conditions are allowed; Critical blockers are not.** Like release certification,
  V0 may certify **with recorded, owned, non-Critical conditions**; any **Critical**
  blocker prevents certification.

## 2. Certification Authority
- The **Founder** is the sole **Certification Authority** (NR-7: no AI self-approval).
- AI agents may **run audits, gather evidence, compute scores, and draft findings**;
  the Founder **reviews and signs** the certification (recorded as an ADR).

## 3. Certification Workflow

```
 GATHER EVIDENCE ─► RUN AUDITS (8 categories) ─► ASSESS READINESS (8 dimensions, scored) ─►
 RISK REVIEW ─► GAP ANALYSIS ─► CHECK EXIT CRITERIA ─► OUTCOME (S5) ─► COMPLETION REPORT + ADR ─►
 (if PASS) V1_READINESS_GATE opens
```
Each step has its own document; this standard governs how they combine into a verdict.

## 4. Certification Evidence
Acceptable evidence is **reproducible and recorded** in the repository:
- **Automated check output** (the CI workflows / their local-equivalent runs):
  link/placeholder/structure/stray-ID/registry scans.
- **Audit results** ([`V0_AUDIT_FRAMEWORK.md`](./V0_AUDIT_FRAMEWORK.md)) per category.
- **Readiness scores** ([`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md)).
- **Risk review** ([`V0_RISK_REVIEW.md`](./V0_RISK_REVIEW.md)) and **gap analysis**
  ([`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md)).
- **Exit-criteria evaluation** ([`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md)).
Evidence that exists only in a conversation is **not** acceptable (the P6 mandate).

## 5. Certification Outcomes
Aligned with [`../quality/RELEASE_CERTIFICATION.md`](../quality/RELEASE_CERTIFICATION.md):

| Outcome | Meaning | V1 may begin? |
|---------|---------|---------------|
| **CERTIFIED** | All exit criteria met; no open condition above Low. | Yes |
| **CERTIFIED WITH CONDITIONS** | All **mandatory** exit criteria met; named, non-Critical conditions remain with owners + remediation points. | Yes (conditions tracked; none blocks V1 start) |
| **DEFERRED** | Specific, achievable evidence/criteria missing; no fundamental blocker. | No — remediate and re-certify |
| **BLOCKED** | A hard blocker exists (a Critical risk, a failed mandatory exit criterion, an architectural contradiction). | No |

## 6. Certification Review Process
1. The Founder reviews the readiness assessment, audit results, risk review, and gap
   analysis **as a set** (they must be mutually consistent).
2. The Founder confirms every **mandatory** exit criterion is met with evidence.
3. The Founder selects the **outcome** (§5) and records it in
   [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md) **and** an **ADR**
   ([`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md)).

## 7. Certification Escalation
- If audits/readiness/risk/gap **disagree**, that inconsistency is itself a finding —
  reconcile before any verdict (no verdict on contradictory evidence).
- If a suspected **Critical** issue appears, the outcome is **BLOCKED** until resolved
  — certification is never forced.
- Disputes resolve to the **Founder** (Certification Authority); the resolution is
  recorded.

## 8. Certification Expiration & Re-certification
- V0 certification is the **permanent record** that V0 completed; it does not
  "expire," but it is **re-validated** whenever the foundation is materially changed
  or after long dormancy (architecture/documentation/context audits — the
  post-dormancy step of [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §5).
- A later finding that the foundation was certified on faulty evidence triggers a
  **postmortem** and re-certification ([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)).

## 9. Relationship To Other Documents
- The certification set: readiness, audit, risk, gap, exit-criteria, completion, V1 gate (this directory).
- Version gate: [`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md), [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md)

Changes to this document are governance-class and require an ADR.
