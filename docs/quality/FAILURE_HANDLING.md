# FAILURE HANDLING

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Derives from:** [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md) §5.3 (Corrective Quality)
> **Integrates:** [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md), [`../governance/Release_Governance.md`](../governance/Release_Governance.md) §8, [`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)

This is the **repository-level failure framework**: a uniform way to handle every
class of failure so that failures are **detected, contained, recovered, learned
from, and prevented from recurring** — never hidden. It turns failures into
durable improvements (preventive quality).

> **Premise:** failures are inevitable; **silent or unlearned** failures are not
> acceptable. Every failure must leave the repository **stronger** (a new
> check/test/rule) and **remembered** (a postmortem + Lore).

---

## 1. The Universal Failure Lifecycle

Every failure, regardless of class, follows the same six stages:

```
 DETECT ─► CONTAIN ─► RECOVER ─► POSTMORTEM ─► PREVENT
    ▲                                            │
    └──────── ESCALATE (any stage, if needed) ───┘
```

| Stage | What it means |
|-------|---------------|
| **Detect** | A check, test, audit, monitor, or human notices the failure. |
| **Escalate** | Route to the right owner; clinical-safety/invariant failures escalate to Founder **immediately**. |
| **Contain** | Stop the bleeding: block the merge, halt the change, or roll back to last known-good. |
| **Recover** | Restore correctness: fix-forward (if trivial+safe) or rollback; verify with tests/gates. |
| **Postmortem** | Capture what happened + root cause ([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)); blameless, durable. |
| **Prevent** | Add/strengthen the check/test/rule so it **cannot recur silently**; record a risk if residual. |

A failure is **not closed** until **Prevent** is done (an incident with no
preventive action remains open — Risk_Governance + Lore).

## 2. Failure Classes

Each class: **Detection · Escalation · Containment · Recovery · Postmortem ·
Prevention.** All map to a risk category ([`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) §1).

### 2.1 Architecture Failures (ARCH)
*Forbidden import, cycle, boundary breach, hidden coupling, rewrite.*
- **Detect:** GCC checks; boundary tests; architecture audit ([`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md)).
- **Escalate:** Founder (Architecture Owner).
- **Contain:** block merge (G1); if merged, revert.
- **Recover:** fix-forward if trivial; else rollback (Architecture_Governance §11).
- **Postmortem:** if it reached `main`. **Prevent:** add/strengthen the GCC/boundary check that missed it.

### 2.2 AI Failures (AI)
*Hallucinated API, context/architecture drift, scope/dependency creep, confident-wrong.*
- **Detect:** AI Review Gate (G3); anti-hallucination; AI-TRACE mismatch ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md)).
- **Escalate:** Founder; reset trust to T0 for that system×artifact pair.
- **Contain:** reject the change (do not "fix in review").
- **Recover:** correct under a compliant prompt; re-validate.
- **Postmortem:** if a **class** of error recurs. **Prevent:** add a guarding check; update the AI risk model / prompt standards.

### 2.3 Testing Failures (TECH)
*Failing guarding test, flaky test, a disabled test, a test that didn't test the invariant.*
- **Detect:** CI (G4); review of test changes.
- **Escalate:** Quality Owner (Founder).
- **Contain:** build red = no merge/release; never disable a guarding test to go green (NR-2).
- **Recover:** fix the code or fix the genuinely-wrong test via a **recorded** change explaining why.
- **Postmortem:** for a missed invariant. **Prevent:** add the missing guarding test.

### 2.4 Governance Failures (COMP)
*Missing ADR, wrong approver, self-approval, misclassified change, gate bypass.*
- **Detect:** Governance Gate (G8); review; audit.
- **Escalate:** Founder.
- **Contain:** block/halt until the correct path is followed.
- **Recover:** create the missing ADR (retroactive ≤72h only for genuine emergencies); reclassify; re-review.
- **Postmortem:** for any gate bypass. **Prevent:** strengthen the gate/automation.

### 2.5 Documentation Failures (REPO)
*Orphaned/conflicting/outdated docs; undefined terms; broken links; ownerless docs.*
- **Detect:** Documentation Gate (G2); doc audit ([`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md)).
- **Escalate:** Documentation Owner (Founder).
- **Contain:** block merge if in the change set.
- **Recover:** reconcile to canonical source; fix links/terms/ownership; mark superseded properly.
- **Postmortem:** for systemic entropy. **Prevent:** add a scan / tighten the index-from-root rule.

### 2.6 Release Failures (OPS / SCALE)
*Failed validation, irreproducible build, missing rollback, post-release regression, (V3+) outage/drift breach.*
- **Detect:** Release Gate (G6); monitoring (V3+).
- **Escalate:** Founder (Release Owner); clinical impact ⇒ immediate.
- **Contain:** Deferred/Blocked certification; (deployed) **rollback** to last known-good (Release_Governance §9).
- **Recover:** remediate; re-certify; re-deploy known-good.
- **Postmortem:** **mandatory** for any deployed incident (Release_Governance §8). **Prevent:** add the validation/monitor that would have caught it.

### 2.7 Context Failures (CTX)
*Undocumented decision/risk/assumption; knowledge only in chat/PR/memory; stale registry; lost rationale; broken recovery.*
- **Detect:** Context Integrity Gate (G7); context audit ([`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)); failed onboarding/recovery validation.
- **Escalate:** Founder.
- **Contain:** block merge until the knowledge is captured into the repository.
- **Recover:** reconstruct from git/Lore; record the missing decision/risk/assumption; refresh state.
- **Postmortem:** for any knowledge that was nearly lost. **Prevent:** strengthen the capture loop ([`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md)) / recovery protocol.

## 3. Severity & Response Speed
Use the risk severity scale (Low/Medium/High/Critical; Risk_Governance §3):
- **Critical** (clinical-safety, invariant breach, data loss): **halt now**, Founder
  immediately, contain before anything else proceeds.
- **High:** address this cycle; block the related gate.
- **Medium:** scheduled remediation; tracked.
- **Low:** monitored; fix on next touch.
Any failure touching a **cross-version invariant or clinical-safety property** is
**≥ High** regardless of probability.

## 4. Stop-and-Remediate vs. Fix-Forward
- **Stop-and-remediate (default for High/Critical):** halt, contain, recover, then resume.
- **Fix-forward (only for trivial + safe + reversible):** correct in place with a
  recorded change; allowed for Low and some Medium failures that do not touch an
  invariant. **Never** fix-forward a clinical-safety or invariant failure silently.

## 5. From Failure to Durable Improvement (the point of this framework)
Every closed failure yields, recorded in the repository:
1. a **postmortem** (Lore) — [`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md);
2. a **prevention** — a new/strengthened check, test, rule, or doc;
3. a **risk update** — closed, or accepted-with-mitigation ([`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md));
4. a **lesson** — [`../context/LESSONS_LEARNED_SYSTEM.md`](../context/LESSONS_LEARNED_SYSTEM.md);
5. a **changelog** entry tying it together.

## 6. Relationship To Other Documents
- Risk: [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) · Release/incident: [`../governance/Release_Governance.md`](../governance/Release_Governance.md) §8
- Postmortems/lessons (V0-P6): [`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md), [`../context/LESSONS_LEARNED_SYSTEM.md`](../context/LESSONS_LEARNED_SYSTEM.md)
- Gates/metrics: [`QUALITY_GATES.md`](./QUALITY_GATES.md), [`QUALITY_METRICS.md`](./QUALITY_METRICS.md)

Changes to this document are governance-class and require an ADR.
