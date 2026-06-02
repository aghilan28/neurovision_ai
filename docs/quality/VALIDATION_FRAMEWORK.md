# VALIDATION FRAMEWORK

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Derives from:** [`QUALITY_PHILOSOPHY.md`](./QUALITY_PHILOSOPHY.md); feeds the **Validation Gate (G5)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document defines the **validation taxonomy**: the categories of validation
the project performs, and for each, the **method, evidence required, approval
requirements, audit requirements, and failure handling.** "Validation" here means
*producing the evidence that a claim is true* — the engine behind the Validation
Gate (G5) and the Release Gate (G6).

> **Premise:** *a claim without validation evidence is not a claim — it is a
> guess.* No result, metric, or "done" status advances without the evidence its
> category requires.

---

## 1. Validation Categories (taxonomy)

| Code | Category | Active from | Primary owner doc |
|------|----------|-------------|-------------------|
| **VC-ARCH** | Architecture validation | V0 | [`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md) |
| **VC-REPO** | Repository validation (structure/entropy) | V0 | [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) + audits |
| **VC-TEST** | Testing validation | V1 | [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) |
| **VC-AI** | AI output validation | V0 | [`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md) |
| **VC-DOC** | Documentation validation | V0 | [`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md) |
| **VC-VER** | Version validation (gate/exit criteria) | V0 | [`../governance/Release_Governance.md`](../governance/Release_Governance.md) + [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md) |
| **VC-REL** | Release validation | V0 | [`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md) |
| **VC-CLIN** | Future clinical validation | V1+ (matures V4) | [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) §clinical |

Each is specified below with the same five fields.

---

## 2. VC-ARCH — Architecture Validation
- **Method:** GCC import/boundary/acyclicity checks; boundary tests; Dependency
  Registry reconciliation; periodic architecture audit ([`ARCHITECTURE_VALIDATION.md`](./ARCHITECTURE_VALIDATION.md)).
- **Evidence required:** acyclic dependency graph; real imports == documented
  contracts; zero forbidden edges; ADRs for every architecture change.
- **Approval requirements:** Founder (Architecture Owner) for A3; GCC must be green.
- **Audit requirements:** full architecture audit at every version gate + quarterly + post-dormancy.
- **Failure handling:** stop-and-remediate; rollback per Architecture_Governance §11; record as ARCH risk + postmortem if it reached `main`.

## 3. VC-REPO — Repository Validation
- **Method:** repository structure check (every directory has a governance README + Owner); entropy scans (orphan/conflict/dead-artifact).
- **Evidence required:** every directory documented + owned; no orphaned/dead files; no duplicated canonical sources.
- **Approval requirements:** Founder; passes the Documentation Gate (G2).
- **Audit requirements:** at every version gate + post-dormancy.
- **Failure handling:** reconcile to canonical source; remove/justify dead artifacts; log defect.

## 4. VC-TEST — Testing Validation
- **Method:** the test categories in [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) /
  [`../governance/Testing_Governance.md`](../governance/Testing_Governance.md) §2.
- **Evidence required:** green invariant/architecture/contract suites; 100% of
  invariant behaviors tested; no disabled guarding test; no regression.
- **Approval requirements:** Founder (Quality Owner); CI green.
- **Audit requirements:** per change (CI) + per version gate (full regression).
- **Failure handling:** stop-and-remediate; never weaken a test to pass (NR-2).

## 5. VC-AI — AI Output Validation
- **Method:** AI-TRACE verification; anti-hallucination symbol resolution; scope/
  dependency diff check; AI risk scoring ([`AI_OUTPUT_VALIDATION.md`](./AI_OUTPUT_VALIDATION.md)).
- **Evidence required:** accurate AI-TRACE; all referenced symbols resolve; no
  silent scope/dependency expansion; human review recorded.
- **Approval requirements:** human (Founder) — **never** the producing agent (NR-7).
- **Audit requirements:** every AI change (G3); AI reliability metric trended ([`QUALITY_METRICS.md`](./QUALITY_METRICS.md)).
- **Failure handling:** reject and return; record an AI-category risk if a class of error recurs.

## 6. VC-DOC — Documentation Validation
- **Method:** the six doc scans (orphan/conflict/staleness/term/link/ownership) +
  documentation quality score ([`DOCUMENTATION_VALIDATION.md`](./DOCUMENTATION_VALIDATION.md)).
- **Evidence required:** all scans pass; quality score ≥ threshold; new terms in Glossary.
- **Approval requirements:** Founder (Documentation Owner); Documentation Gate (G2).
- **Audit requirements:** per merge (touched docs) + full at version gate/quarter/post-dormancy.
- **Failure handling:** fix in the same change set; retire superseded docs properly.

## 7. VC-VER — Version Validation
- **Method:** version-gate checklist; verify **all** this-version exit criteria +
  **no prior-version regression** (NR-12).
- **Evidence required:** every exit criterion met with evidence; architecture +
  documentation + Lore audits passed; no open Critical risk; version-gate ADR.
- **Approval requirements:** **Founder** records the version-gate ADR.
- **Audit requirements:** the gate itself is the audit ([`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md)).
- **Failure handling:** the version does not advance; blockers recorded in [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md).

## 8. VC-REL — Release Validation
- **Method:** release certification ([`RELEASE_CERTIFICATION.md`](./RELEASE_CERTIFICATION.md)).
- **Evidence required:** all gates green; reproducible build; traceability (V2+);
  rollback + observability (V3+); certification outcome recorded.
- **Approval requirements:** Founder (Release Owner); Release Gate (G6).
- **Audit requirements:** per release; tag links to evidence (immutable).
- **Failure handling:** outcome Deferred/Blocked; no tag; reasons recorded.

## 9. VC-CLIN — Future Clinical Validation (V1+; matures to V4)
- **Method:** patient-disjoint (LOSO) evaluation; calibration + conformal coverage;
  held-out-site/montage (domain-shift); abstention behavior — all in `evaluation/`.
- **Evidence required:** metrics **only** on patient-disjoint splits (NR-3);
  measured calibration/coverage (AP-4); shift delta reported (NR-15); reproducible (NR-10).
- **Approval requirements:** Founder; clinical-safety items are **never waivable** (G5).
- **Audit requirements:** every clinical claim; full at version gate.
- **Failure handling:** withhold the claim; the platform may **abstain/escalate**
  rather than emit a low-confidence clinical output (AP-4).
> **Scope note:** "clinical validation" here is **engineering** validation of
> clinical-relevance properties; it is **not** a regulatory-clearance process
> ([`../PROJECT_VISION.md`](../PROJECT_VISION.md) §7).

---

## 10. Validation Evidence Standard (applies to all categories)
Evidence must be:
- **Reproducible** — regenerable from pinned inputs/code (NR-10).
- **Traceable** — linked to the change, ADR, and (if clinical) provenance (NR-11).
- **Recorded** — stored in the repository (registries/changelog/`evaluation/` outputs), **never only** in a chat or someone's memory (the P6 mandate).
- **Audited** — re-checkable by a future agent during recovery.

## 11. Validation ↔ Gate ↔ Metric Map
| Category | Gate | Metric ([`QUALITY_METRICS.md`](./QUALITY_METRICS.md)) |
|----------|------|--------|
| VC-ARCH | G1 | architecture/dependency violations |
| VC-REPO/VC-DOC | G2 | documentation freshness; entropy findings |
| VC-AI | G3 | AI reliability |
| VC-TEST | G4 | test coverage; validation coverage |
| VC-CLIN | G5 | calibration/coverage; shift delta |
| VC-VER | (version gate) | risk closure; decision traceability |
| VC-REL | G6 | release certification rate |

## 12. Relationship To Other Documents
- Gates: [`QUALITY_GATES.md`](./QUALITY_GATES.md) · Tests: [`TEST_STRATEGY.md`](./TEST_STRATEGY.md)
- Architecture/AI/Doc validation: the respective `docs/quality/*` documents
- Governance authorities: Testing/Release/Architecture/Documentation in [`../governance/`](../governance/)

Changes to this document are governance-class and require an ADR.
