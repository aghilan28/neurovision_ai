# V0 AUDIT FRAMEWORK

> **Document type:** Version 0 Certification (V0-P8) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Certification Authority)
> **Update procedure:** Governance-class change (ADR).
> **Feeds:** [`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md), [`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md), [`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md)

The audit framework defines **how V0 is examined**: eight audit categories, each
with a **procedure**, a **checklist**, and **evidence requirements**. The audits
produce the objective evidence that the readiness assessment scores and the
completion report records. Audits reuse the existing audit machinery
(architecture, documentation, context) rather than inventing new checks.

> **Evidence rule:** every audit item is backed by a **re-runnable check** (the CI
> workflows / their local equivalents) or a **linked artifact**. "Looks complete"
> is not evidence.

---

## 1. Audit Categories

| Code | Audit | Source of truth | Primary check |
|------|-------|-----------------|---------------|
| **AUD-ARCH** | Architecture | [`../architecture/`](../architecture/), [`../quality/ARCHITECTURE_VALIDATION.md`](../quality/ARCHITECTURE_VALIDATION.md) | acyclic graph; no forbidden edge; docs present; no stray IDs |
| **AUD-GOV** | Governance | [`../governance/`](../governance/) | 10 docs + index present; change router + ADR framework present |
| **AUD-QUAL** | Quality | [`../quality/`](../quality/) | 11 docs + index; gates G1–G8; metrics M1–M12 |
| **AUD-CTX** | Context | [`../context/`](../context/), [`../../.gcc/`](../../.gcc/) | memory systems + live registers + recovery present/fresh |
| **AUD-ENV** | Environment | [`../environment/`](../environment/), [`../../.github/workflows/`](../../.github/workflows/) | 12 docs + index; 6 workflows; bootstrap/onboarding present |
| **AUD-REPO** | Repository | whole repo | structure; no broken links; no placeholders; ownership |
| **AUD-AI** | AI | [`../governance/AI_Governance.md`](../governance/AI_Governance.md), [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md) | AI workflows + onboarding + AI output validation present |
| **AUD-DOC** | Documentation | all docs | the six doc scans (DOCUMENTATION_VALIDATION §2) |

## 2. Audit Procedures (how each is run)

- **AUD-ARCH:** run `architecture` workflow logic — confirm the five architecture
  docs exist; assert **0 stray AP/NR IDs**; assert the preprocessing-leaf rule is
  documented; (V1+) reconcile real imports vs the allowed graph. Reconcile the
  Dependency Registry.
- **AUD-GOV:** confirm the 10 governance docs + index exist; spot-check that the
  change router, ADR framework, and risk framework are internally consistent and
  reference valid AP/NR IDs.
- **AUD-QUAL:** confirm the 11 quality docs + index; confirm gates G1–G8 and metrics
  M1–M12 are defined and that hard-zero metrics are enumerated.
- **AUD-CTX:** run `context` workflow logic — confirm all memory artifacts exist,
  carry "Last updated", and that assumptions have verification plans; confirm the
  recovery protocol documents a deterministic read order; run CA-1…CA-7
  ([`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)).
- **AUD-ENV:** confirm the 12 environment docs + index and the 6 workflows exist;
  confirm bootstrap + onboarding are deterministic; run EV-1…EV-6
  ([`../environment/ENVIRONMENT_VALIDATION.md`](../environment/ENVIRONMENT_VALIDATION.md)).
- **AUD-REPO:** run `documentation`/`repository-health` logic — structure scan,
  broken-link scan, placeholder scan, ownership scan.
- **AUD-AI:** confirm the approved-AI workflows, the onboarding protocol (hard gate),
  the AI output validation (trust/confidence/risk-scoring), and the AI-TRACE
  requirement all exist and cross-reference correctly.
- **AUD-DOC:** run the six documentation scans (orphan/conflict/staleness/term/link/
  ownership).

## 3. Audit Checklists (per category)

Each audit passes only when **every** item is checked. (Canonical version-gate
checklist: [`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md).)

**AUD-ARCH**
- [ ] 5 architecture docs present.
- [ ] Dependency graph acyclic; import rules explicit.
- [ ] 0 forbidden edges (V1+: real-import scan; V0: docs-only ⇒ N/A by design).
- [ ] 0 stray AP/NR IDs.
- [ ] Dependency Registry reconciled (no unrecorded edge).

**AUD-GOV**
- [ ] 10 governance docs + index present.
- [ ] Change classes + approval paths defined; ADR framework complete.
- [ ] Risk framework (categories/scoring) defined.

**AUD-QUAL**
- [ ] 11 quality docs + index present.
- [ ] Gates G1–G8 defined with blocking/approval criteria.
- [ ] Metrics M1–M12 + RQI + hard-zero set defined.

**AUD-CTX**
- [ ] 10 context docs + index present.
- [ ] Live registers (decisions/risks/assumptions/dependencies) present + fresh.
- [ ] Recovery + onboarding protocols present + deterministic.
- [ ] CA-1…CA-7 pass (no silo / undocumented decision/risk/assumption / orphan).

**AUD-ENV**
- [ ] 12 environment docs + index present.
- [ ] 6 workflows present + runnable (logic verified).
- [ ] Bootstrap + onboarding deterministic; EV-1…EV-6 pass (V0 scope).

**AUD-REPO**
- [ ] Every required directory has a governance README.
- [ ] 0 broken internal links; 0 placeholders in authoritative docs.
- [ ] Every doc declares Owner + Update procedure.

**AUD-AI**
- [ ] Approved AI systems + workflows defined; AI failure modes enumerated.
- [ ] AI onboarding is a hard gate; context recovery deterministic.
- [ ] AI output validation (trust/confidence/risk) + AI-TRACE defined.

**AUD-DOC**
- [ ] Six doc scans clean; new terms in Glossary; reading order navigable.

## 4. Audit Evidence Requirements
For each category, the certification retains: the **check output** (or its local
run), the **list of artifacts** verified, and any **findings** (which become gaps/
risks). Evidence is reproducible and recorded (linked from
[`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md)).

## 5. Audit → Readiness → Outcome
The audit results are the inputs to the readiness scores
([`V0_READINESS_ASSESSMENT.md`](./V0_READINESS_ASSESSMENT.md)); findings feed the
gap analysis ([`V0_GAP_ANALYSIS.md`](./V0_GAP_ANALYSIS.md)) and risk review
([`V0_RISK_REVIEW.md`](./V0_RISK_REVIEW.md)); the combined picture yields the
certification outcome.

Changes to this document are governance-class and require an ADR.
