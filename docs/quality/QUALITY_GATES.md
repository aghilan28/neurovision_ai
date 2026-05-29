# QUALITY GATES

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Derives from:** [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md)
> **Enforces / wraps:** [`../governance/Review_Governance.md`](../governance/Review_Governance.md), [`../governance/Release_Governance.md`](../governance/Release_Governance.md), [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md), [`../governance/Change_Management.md`](../governance/Change_Management.md)

A **quality gate** is a mandatory checkpoint a change or release must pass before
proceeding. Gates make the philosophy enforceable: nothing advances on assertion,
only on **evidence**. Gates **wrap** the governance checkpoints (they do not
replace them) and are mechanized by GCC + tests + review wherever possible.

> **Gate principle:** a gate is **blocking by default.** A gate is passed only when
> its approval criteria are met with evidence; otherwise it **fails** and triggers
> its failure action. "Looks fine" is never a pass.

---

## 1. The Eight Gates (and when they apply)

| Gate | Applies to | Mechanized by |
|------|-----------|---------------|
| **G1 Architecture Gate** | Any architecture-class (A3) change | GCC import/boundary/acyclicity + architecture review |
| **G2 Documentation Gate** | Any change touching docs / any merge | Doc audit (orphan/conflict/staleness/term/link/ownership) |
| **G3 AI Review Gate** | Any AI-generated change | AI-TRACE check + ai-review checklist + human review |
| **G4 Testing Gate** | Any code change (V1+) | Test suites + coverage of invariants |
| **G5 Validation Gate** | Any result/claim (V1+) | Validation evidence per [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) |
| **G6 Release Gate** | Any release/version tag | Release certification |
| **G7 Context Integrity Gate** | Any merge; every version gate; post-dormancy | Context audit (decisions/risks/assumptions/Lore) |
| **G8 Governance Gate** | Any A2+ / governance change | ADR present + change classified + approver correct |

A change passes **all gates that apply to it**; a release passes **all eight**.
Gate order in practice: automated gates (G1–G2 checks, G4) run first; human gates
(G3 review, G8) next; G5/G7 evidence confirmed; G6 last (release only).

---

## 2. Gate Specifications

Each gate is specified with: **Purpose · Owner · Inputs · Outputs · Blocking
criteria · Approval criteria · Failure action · Escalation.**

### G1 — Architecture Gate
- **Purpose:** prevent architecture drift, cycles, boundary breaches, rewrites.
- **Owner:** Founder (Architecture Owner). **Mechanized:** GCC + boundary/acyclicity tests.
- **Inputs:** the diff; affected modules; RFC/ADR; impact analysis.
- **Outputs:** pass/fail + architecture-review record.
- **Blocking criteria:** any forbidden import / cycle (NR-8); a rewrite (NR-6); a
  weakened invariant; an architecture change **without an approved ADR** (NR-5);
  unrecorded dependency edge.
- **Approval criteria:** [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) §6.1 + §12 checklist fully satisfied.
- **Failure action:** stop-and-remediate; reject/abandon or rollback (Architecture_Governance §11).
- **Escalation:** Founder; if a principle/rule seems violated, **halt** and open a governance decision.

### G2 — Documentation Gate
- **Purpose:** keep docs true, singular, current, navigable (no entropy).
- **Owner:** Founder (Documentation Owner). **Mechanized:** doc audit scans.
- **Inputs:** changed docs; the doc set; the Glossary.
- **Outputs:** audit result (orphan/conflict/staleness/term/link/ownership).
- **Blocking criteria:** an orphaned doc; a conflict with a higher tier; a new term
  not in the Glossary (NR-14); a broken internal link; a doc with no Owner/Update
  procedure; a stale Tier-3 state file.
- **Approval criteria:** all six doc scans pass ([`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md); [`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §8).
- **Failure action:** fix in the same change set; relog.
- **Escalation:** Documentation Owner (Founder).

### G3 — AI Review Gate
- **Purpose:** ensure AI-generated work is verified by a human and free of
  hallucination/scope/dependency drift.
- **Owner:** Founder (reviewer). **Mechanized:** AI-TRACE presence check.
- **Inputs:** the AI change + its **AI-TRACE block** ([`../governance/AI_Governance.md`](../governance/AI_Governance.md) §9).
- **Outputs:** ai-review record + AI risk score ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md)).
- **Blocking criteria:** missing/inaccurate AI-TRACE; any **hallucinated symbol**;
  silent scope or dependency expansion; **self-approval** (NR-7).
- **Approval criteria:** [`../.gcc/CHECKLISTS/ai_review_checklist.md`](../../.gcc/CHECKLISTS/ai_review_checklist.md) passed by a human reviewer.
- **Failure action:** reject (do not "fix in review"); return with the specific failure.
- **Escalation:** Founder.

### G4 — Testing Gate
- **Purpose:** make invariants executable; block regressions.
- **Owner:** Founder (Quality Owner). **Mechanized:** test suites + CI.
- **Inputs:** the change + its tests.
- **Outputs:** green/red build + coverage-of-invariants evidence.
- **Blocking criteria:** any failing invariant/architecture/contract test; a
  **disabled guarding test** (NR-2 hidden debt); a prior-version regression; missing
  required tests for the touched behavior.
- **Approval criteria:** [`../governance/Testing_Governance.md`](../governance/Testing_Governance.md) §6 gating satisfied; invariant behaviors 100% covered.
- **Failure action:** stop-and-remediate; never disable a guarding test to go green.
- **Escalation:** Quality Owner (Founder).

### G5 — Validation Gate
- **Purpose:** ensure every result/claim has the required evidence.
- **Owner:** Founder (Quality Owner). **Mechanized:** validation evidence checks.
- **Inputs:** the claim/result + its validation evidence.
- **Outputs:** validation record (method, evidence, outcome).
- **Blocking criteria:** a metric on a **non-patient-disjoint** split (NR-3); a
  result that is **not reproducible** (NR-10); a generalization claim **without
  held-out-site** evidence (NR-15); a clinical output **without calibrated
  uncertainty** (NR-4); a clinical output **not traceable** (NR-11).
- **Approval criteria:** evidence required by [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) for the claim's category is present and audited.
- **Failure action:** withhold the claim; remediate; record.
- **Escalation:** Founder; clinical-safety concerns escalate immediately.

### G6 — Release Gate
- **Purpose:** certify a release is reproducible, traceable, regression-free, and
  (V3+) deployable with rollback + observability.
- **Owner:** Founder (Release Owner). **Mechanized:** release certification.
- **Inputs:** the release candidate + all gate results + version-gate status.
- **Outputs:** a **certification outcome**: Approved / Approved with Risk /
  Deferred / Blocked ([`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md)).
- **Blocking criteria:** any failing gate above; a version-skip (NR-12); an open
  **Critical** risk; missing rollback/observability (V3+).
- **Approval criteria:** [`../.gcc/CHECKLISTS/release_checklist.md`](../../.gcc/CHECKLISTS/release_checklist.md) + release certification satisfied; Founder approval recorded.
- **Failure action:** Deferred or Blocked; record reasons; no tag.
- **Escalation:** Founder (sole approver).

### G7 — Context Integrity Gate
- **Purpose:** guarantee no knowledge is lost — every consequential change leaves
  recoverable context.
- **Owner:** Founder. **Mechanized:** context audit ([`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)).
- **Inputs:** the change + decisions/risks/assumptions/Lore touched.
- **Outputs:** context audit result.
- **Blocking criteria:** an undocumented decision (NR-5); an undocumented risk or
  assumption; knowledge that exists **only** in a chat/PR comment/founder memory;
  a stale registry; a broken decision↔change↔risk link.
- **Approval criteria:** decisions/risks/assumptions recorded; changelog + Lore
  updated; context recovery still deterministic ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)).
- **Failure action:** capture the missing knowledge into the repository before merge.
- **Escalation:** Founder.

### G8 — Governance Gate
- **Purpose:** ensure the change went through the correct governance path.
- **Owner:** Founder. **Mechanized:** change-class + ADR presence checks.
- **Inputs:** the change + its class + ADR/RFC.
- **Outputs:** governance record.
- **Blocking criteria:** a misclassified change; an A2+ change without an ADR
  (NR-5); wrong/absent approver (NR-7); out-of-scope (NR-13); version-skip (NR-12).
- **Approval criteria:** [`../governance/Change_Management.md`](../governance/Change_Management.md) path satisfied for the change's class.
- **Failure action:** route to the correct path; do not proceed until satisfied.
- **Escalation:** Founder.

---

## 3. Gate Applicability Matrix

| Change type | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 |
|-------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Documentation (A0/A1) | – | ✅ | if AI | – | – | – | ✅ | if meaning |
| Minor (A1) | – | ✅ | if AI | ✅ (V1+) | if claim | – | ✅ | – |
| Major (A2) | – | ✅ | if AI | ✅ | ✅ | – | ✅ | ✅ |
| Architecture (A3) | ✅ | ✅ | if AI | ✅ | ✅ | – | ✅ | ✅ |
| Governance (A3) | if arch | ✅ | if AI | – | – | – | ✅ | ✅ |
| Release / version gate | ✅ | ✅ | – | ✅ | ✅ | ✅ | ✅ | ✅ |

("if AI" = applies when the change is AI-generated; "if claim" = applies when the
change reports a result/metric.)

## 4. Gate Exceptions
- A gate may be **temporarily** waived **only** by the Founder, **only** with a
  recorded ADR stating the rationale, the **compensating control**, and an expiry,
  **and** a debt record (NR-2). **Clinical-safety and validation-integrity gates
  (G5 clinical items, G4 invariants) are never waived.**
- An AI agent can **never** waive a gate.

## 5. Relationship To Other Documents
- Philosophy: [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md) · Validation: [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)
- Metrics (gate health): [`QUALITY_METRICS.md`](./QUALITY_METRICS.md) · Failures: [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md)
- Governance checkpoints wrapped: Review/Release/Architecture/Change in [`../governance/`](../governance/)

Changes to this document are governance-class and require an ADR.
